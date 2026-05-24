"""Generic numerical feature engineering used by the CMAPSS pipeline.

1. ``drop_bad_columns`` — remove all-NaN, near-constant, or > 30% NaN columns.
2. ``standardize`` — per-column z-score, zero-variance-safe.
3. ``aggregate_windows`` — resample a DatetimeIndex frame into fixed-width
   windows producing ``<sensor>__<stat>`` columns. Not used in the per-cycle
   CMAPSS classification path; kept for downstream work that needs it.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def drop_bad_columns(
    df: pd.DataFrame,
    *,
    max_nan_frac: float = 0.30,
    min_variance: float = 1e-12,
) -> pd.DataFrame:
    nan_frac = df.isna().mean()
    keep_nan = nan_frac <= max_nan_frac
    var = df.var(numeric_only=True)
    keep_var = var > min_variance
    keep = keep_nan & keep_var
    dropped = list(df.columns[~keep])
    if dropped:
        print(f"  dropping {len(dropped)} bad columns "
              f"(>{max_nan_frac:.0%} NaN or near-constant): "
              f"{dropped[:5]}{'...' if len(dropped) > 5 else ''}", flush=True)
    return df.loc[:, keep].astype("float32")


def standardize(df: pd.DataFrame) -> pd.DataFrame:
    mu = df.mean(numeric_only=True)
    sd = df.std(numeric_only=True).replace(0, 1)
    out = ((df - mu) / sd).astype("float32")
    return out


def aggregate_windows(
    df: pd.DataFrame,
    *,
    window: str = "60s",
    stats: tuple[str, ...] = ("mean", "std"),
) -> pd.DataFrame:
    """Aggregate a 1 Hz HAI frame into ``window``-wide bins.

    Output columns are flattened: ``<sensor>__<stat>``.
    """
    rs = df.resample(window)
    pieces = []
    for stat in stats:
        agg = getattr(rs, stat)()
        agg.columns = [f"{c}__{stat}" for c in agg.columns]
        pieces.append(agg)
    out = pd.concat(pieces, axis=1).dropna(how="all")
    return out.astype("float32")


def build_features(
    raw: pd.DataFrame,
    *,
    window: str = "60s",
    stats: tuple[str, ...] = ("mean", "std"),
    max_nan_frac: float = 0.30,
) -> pd.DataFrame:
    """End-to-end: drop bad columns → standardize → aggregate to windows.

    Standardization happens *before* aggregation so the per-bin mean/std
    are in z-units, comparable across sensors with wildly different
    physical scales (bar vs. °C vs. RPM).
    """
    clean = drop_bad_columns(raw, max_nan_frac=max_nan_frac)
    z = standardize(clean)
    feats = aggregate_windows(z, window=window, stats=stats)
    print(f"  features: {feats.shape[0]:,} rows × {feats.shape[1]} cols "
          f"(window={window}, stats={stats})", flush=True)
    return feats


def downsample_labels(
    attack_id: pd.Series,
    feature_index: pd.DatetimeIndex,
    *,
    window: str = "60s",
) -> pd.Series:
    """Reduce per-second attack-id labels to per-window labels.

    A window is labelled as attack if ANY second within it was an attack.
    The attack id used is the max over the window (stable for non-
    overlapping attacks).
    """
    binned = attack_id.resample(window).max().reindex(feature_index, method="nearest")
    return binned.fillna(0).astype("int32").rename("attack_id")
