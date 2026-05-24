"""End-to-end CMAPSS pipeline orchestrator.

For each subset in FD001..FD004 and each failure window W in {20, 50}:
    1. Load and split engines 60/20/20.
    2. Tune + fit a LightGBM binary classifier on the train split.
    3. Predict probabilities + native LightGBM SHAP on test and validate.
    4. Save the booster (.txt), per-row predictions+RUL (.parquet),
       per-row SHAP (.parquet), and summary metrics (.json).

Run:
    python -m src.cmapss.artifacts
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    roc_auc_score,
)

from src.cmapss.load import (
    SUBSETS,
    download_cmapss,
    feature_columns,
    read_subset,
)
from src.cmapss.split import DEFAULT_WINDOWS, split_engines
from src.cmapss.train import TrainedModel, predict_with_shap, train_window_classifier
from src.features import drop_bad_columns, standardize

ROOT = Path(__file__).resolve().parents[2]


# ----------------------------------------------------------- helpers

def _prepare_features(splits, feat_cols):
    """Drop bad columns (per training data), then z-score all three splits
    using the training mean/std. Returns (train, test, validate) with
    feature columns standardized and other columns untouched.
    """
    train_feats = splits.train[feat_cols].astype("float32")
    kept = drop_bad_columns(train_feats).columns.tolist()

    mu = splits.train[kept].mean()
    sd = splits.train[kept].std().replace(0, 1)

    def _apply(df):
        df = df.copy()
        df[kept] = ((df[kept] - mu) / sd).astype("float32")
        # Drop sensors that were filtered out so test/val match the model's input
        for c in feat_cols:
            if c not in kept and c in df.columns:
                df.drop(columns=c, inplace=True)
        return df

    return _apply(splits.train), _apply(splits.test), _apply(splits.validate), kept


def _eval_metrics(y_true: np.ndarray, y_prob: np.ndarray) -> dict:
    """Compute the standard scalar metrics + a few operational ones."""
    if y_true.sum() == 0 or y_true.sum() == len(y_true):
        return {"note": "degenerate split (single-class)", "n": int(len(y_true)),
                "positives": int(y_true.sum())}
    roc = float(roc_auc_score(y_true, y_prob))
    ap = float(average_precision_score(y_true, y_prob))
    brier = float(brier_score_loss(y_true, y_prob))
    # Youden-optimal threshold via ROC sweep
    order = np.argsort(-y_prob)
    y_sorted = y_true[order]
    tp = np.cumsum(y_sorted)
    fp = np.cumsum(1 - y_sorted)
    P = y_true.sum()
    N = len(y_true) - P
    tpr = tp / max(P, 1)
    fpr = fp / max(N, 1)
    j = tpr - fpr
    star = int(np.argmax(j))
    thr = float(np.sort(y_prob)[::-1][star])
    pred = (y_prob >= thr).astype(np.int8)
    tn, fp_, fn_, tp_ = confusion_matrix(y_true, pred, labels=[0, 1]).ravel()
    # precision@top-1% (per-fleet, not per-engine, to keep it scalar)
    k = max(1, int(0.01 * len(y_true)))
    top_idx = np.argsort(-y_prob)[:k]
    p_at_k = float(y_true[top_idx].mean())
    return {
        "n": int(len(y_true)),
        "positives": int(P),
        "positive_rate": float(P / len(y_true)),
        "roc_auc": roc,
        "auc_pr": ap,
        "brier": brier,
        "youden_threshold": thr,
        "tp": int(tp_), "fp": int(fp_), "fn": int(fn_), "tn": int(tn),
        f"precision_at_top_{k}": p_at_k,
    }


def _shap_frame(
    df: pd.DataFrame,
    shap_values: np.ndarray,
    probabilities: np.ndarray,
    feature_names: list[str],
    base_value: float,
) -> pd.DataFrame:
    """Wrap raw SHAP values into a tidy parquet-ready frame.

    Row order matches ``df``; row keys (engine_id, cycle, timestamp, RUL,
    predicted_prob, base_value) are attached so the Streamlit app can do
    a single read.
    """
    out = pd.DataFrame(shap_values, columns=[f"shap__{c}" for c in feature_names],
                        index=df.index)
    out.insert(0, "engine_id", df["engine_id"].to_numpy())
    out.insert(1, "cycle", df["cycle"].to_numpy())
    out.insert(2, "timestamp", df["timestamp"].to_numpy())
    out.insert(3, "RUL", df["RUL"].to_numpy())
    out["predicted_prob"] = probabilities
    out["base_value"] = base_value
    return out


def _predictions_frame(
    df: pd.DataFrame,
    probabilities: np.ndarray,
    target_col: str,
) -> pd.DataFrame:
    """Per-row prediction frame: engine_id, cycle, RUL, true label, prob."""
    return pd.DataFrame({
        "engine_id": df["engine_id"].to_numpy(),
        "cycle": df["cycle"].to_numpy(),
        "timestamp": df["timestamp"].to_numpy(),
        "RUL": df["RUL"].to_numpy(),
        "y_true": df[target_col].to_numpy(),
        "predicted_prob": probabilities,
    })


# ----------------------------------------------------------- per-subset

def process_subset(
    subset: str,
    *,
    data_dir: Path,
    models_dir: Path,
    eval_dir: Path,
    windows: tuple[int, ...],
    n_trials: int,
    seed: int,
) -> dict:
    t0 = time.time()
    print(f"\n=== {subset} ===", flush=True)
    raw = read_subset(subset, data_dir)
    feat_cols = feature_columns(raw)
    print(f"  raw: {len(raw):,} rows, {raw['engine_id'].nunique()} engines, "
          f"{len(feat_cols)} feature columns", flush=True)

    splits = split_engines(raw, seed=seed, windows=windows)
    print(f"  split: train={splits.train['engine_id'].nunique()}, "
          f"test={splits.test['engine_id'].nunique()}, "
          f"validate={splits.validate['engine_id'].nunique()} engines", flush=True)

    train_df, test_df, val_df, kept_feats = _prepare_features(splits, feat_cols)
    print(f"  kept features after drop_bad_columns: {len(kept_feats)}", flush=True)

    per_window: dict = {}
    for w in windows:
        target = f"y_{w}"
        print(f"  --- window={w} (target={target}) ---", flush=True)
        print(f"  train positive rate: {train_df[target].mean():.4f}", flush=True)

        model = train_window_classifier(
            train_df,
            feature_names=kept_feats,
            target_col=target,
            n_trials=n_trials,
            seed=seed,
        )
        print(f"  best CV AUC-PR = {model.cv_auc_pr:.4f}", flush=True)

        model_path = models_dir / f"lgbm_{subset}_w{w}.txt"
        model.save(model_path)

        # Test
        prob_t, shap_t, base_t = predict_with_shap(model, test_df)
        test_metrics = _eval_metrics(test_df[target].to_numpy(), prob_t)
        print(f"  TEST  AUC-PR={test_metrics.get('auc_pr', float('nan')):.4f} "
              f"ROC-AUC={test_metrics.get('roc_auc', float('nan')):.4f}", flush=True)
        _predictions_frame(test_df, prob_t, target).to_parquet(
            eval_dir / f"predictions_{subset}_w{w}.parquet", index=False
        )
        _shap_frame(test_df, shap_t, prob_t, kept_feats, base_t).to_parquet(
            eval_dir / f"shap_{subset}_w{w}.parquet", index=False
        )

        # Validate
        prob_v, shap_v, base_v = predict_with_shap(model, val_df)
        val_metrics = _eval_metrics(val_df[target].to_numpy(), prob_v)
        print(f"  VAL   AUC-PR={val_metrics.get('auc_pr', float('nan')):.4f} "
              f"ROC-AUC={val_metrics.get('roc_auc', float('nan')):.4f}", flush=True)
        _predictions_frame(val_df, prob_v, target).to_parquet(
            eval_dir / f"validation_predictions_{subset}_w{w}.parquet", index=False
        )
        _shap_frame(val_df, shap_v, prob_v, kept_feats, base_v).to_parquet(
            eval_dir / f"validation_shap_{subset}_w{w}.parquet", index=False
        )

        summary = {
            "subset": subset,
            "window": w,
            "model_path": str(model_path.relative_to(ROOT)),
            "cv_auc_pr": model.cv_auc_pr,
            "best_params": model.best_params,
            "features": kept_feats,
            "test": test_metrics,
            "validate": val_metrics,
        }
        (eval_dir / f"metrics_{subset}_w{w}.json").write_text(
            json.dumps(summary, indent=2, default=str)
        )
        per_window[w] = summary

    print(f"  {subset} done in {time.time() - t0:.1f}s", flush=True)
    return {"subset": subset, "windows": per_window}


# ----------------------------------------------------------- CLI

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--subsets", nargs="+", default=list(SUBSETS),
                    help="CMAPSS subsets to process (default: all four)")
    ap.add_argument("--windows", nargs="+", type=int, default=list(DEFAULT_WINDOWS),
                    help="Failure windows in cycles (default: 20 50)")
    ap.add_argument("--n-trials", type=int, default=30,
                    help="Optuna trials per (subset, window) (default: 30)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--data-dir", type=Path, default=ROOT / "data" / "cmapss")
    ap.add_argument("--models-dir", type=Path, default=ROOT / "models")
    ap.add_argument("--eval-dir", type=Path, default=ROOT / "eval")
    args = ap.parse_args()

    args.models_dir.mkdir(parents=True, exist_ok=True)
    args.eval_dir.mkdir(parents=True, exist_ok=True)

    print(f"data_dir = {args.data_dir}")
    download_cmapss(args.data_dir)

    all_summaries = []
    for sub in args.subsets:
        all_summaries.append(process_subset(
            sub,
            data_dir=args.data_dir,
            models_dir=args.models_dir,
            eval_dir=args.eval_dir,
            windows=tuple(args.windows),
            n_trials=args.n_trials,
            seed=args.seed,
        ))

    (args.eval_dir / "summary.json").write_text(
        json.dumps(all_summaries, indent=2, default=str)
    )
    print("\nAll done.", flush=True)


if __name__ == "__main__":
    main()
