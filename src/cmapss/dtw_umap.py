"""Pre-compute multivariate-DTW + UMAP embeddings per CMAPSS subset.

For each subset, for every engine in the union (train + test + validate):
    1. Z-score the engine's sensor trajectory using the training-split
       mean/std (same standardization the LightGBM model saw).
    2. Restrict to the top-K features by the model's mean-|SHAP|-on-
       validation (so the DTW signal is the channels the model actually
       relies on, not noise).
    3. Compute pairwise multivariate DTW with a Sakoe-Chiba band.
    4. Fit UMAP on the precomputed distance matrix to get a 2-D embedding.

Outputs (per subset ``S``):
    eval/dtw_distance_{S}.npy            engine x engine float32 matrix
    eval/dtw_umap_{S}.parquet            per-engine (x, y) + metadata
    eval/dtw_meta_{S}.json               feature list, params, runtime

The Streamlit app loads ``dtw_umap_{S}.parquet`` only --- a 2-D scatter
with metadata for hover/color. The distance matrix is kept around for
re-fits with different UMAP params.

Run:
    python -m src.cmapss.dtw_umap                 # all 4 subsets
    python -m src.cmapss.dtw_umap --subsets FD001 # one subset
    python -m src.cmapss.dtw_umap --top-k 6       # fewer DTW channels
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from tslearn.metrics import cdist_dtw
import umap

from src.cmapss.load import SUBSETS, download_cmapss, feature_columns, read_subset
from src.cmapss.split import split_engines
from src.features import drop_bad_columns

ROOT = Path(__file__).resolve().parents[2]
EVAL = ROOT / "eval"
DATA = ROOT / "data" / "cmapss"

# Knobs (CLI-overridable)
DEFAULT_TOP_K = 8
DEFAULT_SAKOE_CHIBA = 10
DEFAULT_UMAP_NEIGHBORS = 15
DEFAULT_UMAP_MIN_DIST = 0.1
DEFAULT_SEED = 42


def _top_features(subset: str, k: int) -> list[str]:
    """Top-K features by mean|SHAP| on the validation split, W=50.

    W=50 is the denser target (positive rate ~25%), so its global SHAP
    ranks are more stable than W=20's. The set of channels chosen here
    drives the DTW signal.
    """
    shap = pd.read_parquet(EVAL / f"validation_shap_{subset}_w50.parquet")
    cols = [c for c in shap.columns if c.startswith("shap__")]
    mean_abs = (
        shap[cols]
        .abs()
        .mean()
        .rename(lambda s: s[len("shap__"):])
        .sort_values(ascending=False)
    )
    return mean_abs.head(k).index.tolist()


def _standardize_per_subset(subset: str, feat_cols: list[str], seed: int):
    """Reproduce the orchestrator's standardization to keep model and
    DTW inputs aligned. Drops the same near-constant columns the model
    saw, then z-scores against the training-split mean/std.

    Returns the standardized long DataFrame (engine_id, cycle, ...standardized features).
    """
    raw = read_subset(subset, DATA)
    splits = split_engines(raw, seed=seed)
    train_feat = splits.train[feat_cols].astype("float32")
    kept = drop_bad_columns(train_feat).columns.tolist()

    mu = splits.train[kept].mean()
    sd = splits.train[kept].std().replace(0, 1)

    out = raw[["engine_id", "cycle"] + kept].copy()
    out[kept] = ((out[kept] - mu) / sd).astype("float32")
    return out, kept, splits


def _engine_arrays(df: pd.DataFrame, channels: list[str]) -> tuple[np.ndarray, list[int]]:
    """Build a (N_engines, T_max, D) padded tensor + matching engine IDs.

    tslearn.metrics.cdist_dtw expects a 3-D array; sequences of different
    lengths must be padded with NaN, which tslearn handles natively.
    """
    engine_ids = sorted(df["engine_id"].unique().tolist())
    seqs = []
    for eid in engine_ids:
        g = df.loc[df["engine_id"] == eid].sort_values("cycle")
        seqs.append(g[channels].to_numpy(dtype=np.float32))
    t_max = max(len(s) for s in seqs)
    d = len(channels)
    padded = np.full((len(seqs), t_max, d), np.nan, dtype=np.float32)
    for i, s in enumerate(seqs):
        padded[i, : len(s), :] = s
    return padded, engine_ids


def _per_engine_metadata(
    subset: str, engine_ids: list[int], splits, raw: pd.DataFrame
) -> pd.DataFrame:
    """Pull per-engine attributes the UMAP scatter will color/hover by.

    For every engine (including train), we compute its failure cycle from
    the raw CMAPSS data (engines run to failure in train_FDxxx.txt).
    For test + validate engines we additionally surface the model's
    W=50 peak P(class=1) and the SHAP-peak feature at that cycle. Train
    engines have ``max_prob_w50 = NaN`` and ``top_feature_at_peak = ''``.
    """
    # Failure cycle = max cycle per engine in the raw run-to-failure data.
    fail_cycle = (
        raw.groupby("engine_id")["cycle"].max().astype(int).to_dict()
    )

    split_lookup: dict[int, str] = {}
    for name, df in splits.items():
        for eid in df["engine_id"].unique():
            split_lookup[int(eid)] = name

    pred_test = pd.read_parquet(EVAL / f"predictions_{subset}_w50.parquet")
    pred_val = pd.read_parquet(EVAL / f"validation_predictions_{subset}_w50.parquet")
    shap_test = pd.read_parquet(EVAL / f"shap_{subset}_w50.parquet")
    shap_val = pd.read_parquet(EVAL / f"validation_shap_{subset}_w50.parquet")
    pred = pd.concat([pred_test, pred_val], ignore_index=True)
    shap = pd.concat([shap_test, shap_val], ignore_index=True)

    pred_by_eng = {int(eid): grp for eid, grp in pred.groupby("engine_id")}
    shap_by_eng = {int(eid): grp for eid, grp in shap.groupby("engine_id")}
    shap_cols = [c for c in shap.columns if c.startswith("shap__")]

    rows = []
    for eid in engine_ids:
        eid = int(eid)
        split_name = split_lookup.get(eid, "unknown")
        if eid in pred_by_eng:
            g = pred_by_eng[eid].sort_values("cycle")
            peak = g["predicted_prob"].idxmax()
            peak_row = g.loc[peak]
            cycle_at_peak = int(peak_row["cycle"])
            max_prob = float(peak_row["predicted_prob"])
            sg = shap_by_eng[eid]
            sr = sg.loc[(sg["cycle"] == cycle_at_peak)].iloc[0]
            top_feat = sr[shap_cols].abs().idxmax()[len("shap__"):]
        else:
            cycle_at_peak = -1
            max_prob = float("nan")
            top_feat = ""
        rows.append({
            "engine_id": eid,
            "split": split_name,
            "failure_cycle": int(fail_cycle.get(eid, -1)),
            "max_prob_w50": max_prob,
            "cycle_at_peak": cycle_at_peak,
            "top_feature_at_peak": top_feat,
        })
    return pd.DataFrame(rows)


def process_subset(
    subset: str,
    *,
    top_k: int,
    sakoe_chiba: int,
    umap_neighbors: int,
    umap_min_dist: float,
    seed: int,
) -> dict:
    t0 = time.time()
    print(f"\n=== {subset}: precomputing DTW + UMAP ===", flush=True)

    # 1) Pick the channels the model leans on
    channels = _top_features(subset, top_k)
    print(f"  top-{top_k} channels by mean|SHAP|(W=50): {channels}", flush=True)

    # 2) Standardize against train mean/std (orchestrator-consistent)
    raw = read_subset(subset, DATA)
    feat_cols = feature_columns(raw)
    std_df, kept, splits = _standardize_per_subset(subset, feat_cols, seed)
    # Sanity: keep only channels that survived drop_bad_columns
    channels = [c for c in channels if c in kept]
    print(f"  after drop_bad_columns reconciliation: {len(channels)} channels", flush=True)

    # 3) Build padded (engines, T, D) array
    padded, engine_ids = _engine_arrays(std_df, channels)
    print(f"  shape: {padded.shape}  (engines × T × channels)", flush=True)

    # 4) Pairwise DTW with Sakoe-Chiba band
    t_dtw = time.time()
    D = cdist_dtw(
        padded, padded,
        global_constraint="sakoe_chiba",
        sakoe_chiba_radius=sakoe_chiba,
        n_jobs=-1,
        verbose=0,
    ).astype("float32")
    print(f"  DTW done in {time.time() - t_dtw:.1f}s  ({D.shape[0]} engines, "
          f"radius={sakoe_chiba}, n_jobs=-1)", flush=True)
    np.save(EVAL / f"dtw_distance_{subset}.npy", D)

    # 5) UMAP from precomputed distance matrix
    t_umap = time.time()
    reducer = umap.UMAP(
        n_neighbors=min(umap_neighbors, max(2, len(engine_ids) - 1)),
        min_dist=umap_min_dist,
        n_components=2,
        metric="precomputed",
        random_state=seed,
    )
    coords = reducer.fit_transform(D)
    print(f"  UMAP done in {time.time() - t_umap:.1f}s", flush=True)

    # 6) Save embedding + metadata
    meta = _per_engine_metadata(subset, engine_ids, splits, raw)
    meta["umap_x"] = coords[:, 0].astype("float32")
    meta["umap_y"] = coords[:, 1].astype("float32")
    meta.to_parquet(EVAL / f"dtw_umap_{subset}.parquet", index=False)

    summary = {
        "subset": subset,
        "n_engines": len(engine_ids),
        "channels": channels,
        "sakoe_chiba_radius": sakoe_chiba,
        "umap_n_neighbors": umap_neighbors,
        "umap_min_dist": umap_min_dist,
        "seed": seed,
        "elapsed_seconds": round(time.time() - t0, 2),
    }
    (EVAL / f"dtw_meta_{subset}.json").write_text(json.dumps(summary, indent=2))
    print(f"  {subset} done in {summary['elapsed_seconds']}s", flush=True)
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--subsets", nargs="+", default=list(SUBSETS))
    ap.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    ap.add_argument("--sakoe-chiba", type=int, default=DEFAULT_SAKOE_CHIBA)
    ap.add_argument("--umap-neighbors", type=int, default=DEFAULT_UMAP_NEIGHBORS)
    ap.add_argument("--umap-min-dist", type=float, default=DEFAULT_UMAP_MIN_DIST)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = ap.parse_args()

    EVAL.mkdir(parents=True, exist_ok=True)
    download_cmapss(DATA)

    all_summaries = []
    for sub in args.subsets:
        all_summaries.append(process_subset(
            sub,
            top_k=args.top_k,
            sakoe_chiba=args.sakoe_chiba,
            umap_neighbors=args.umap_neighbors,
            umap_min_dist=args.umap_min_dist,
            seed=args.seed,
        ))
    (EVAL / "dtw_summary.json").write_text(json.dumps(all_summaries, indent=2))
    print("\nAll DTW + UMAP precomputation done.", flush=True)


if __name__ == "__main__":
    main()
