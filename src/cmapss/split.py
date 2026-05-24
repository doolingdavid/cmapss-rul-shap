"""Engine-grouped train/test/validate split + RUL target construction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

DEFAULT_WINDOWS: tuple[int, ...] = (20, 50)
DEFAULT_FRACTIONS = (0.60, 0.20, 0.20)  # train / test / validate
DEFAULT_SEED = 42


@dataclass(frozen=True)
class Splits:
    """Three DataFrames keyed by split name (train/test/validate)."""

    train: pd.DataFrame
    test: pd.DataFrame
    validate: pd.DataFrame

    def __getitem__(self, key: str) -> pd.DataFrame:
        return {"train": self.train, "test": self.test, "validate": self.validate}[key]

    def items(self):
        return [("train", self.train), ("test", self.test), ("validate", self.validate)]


def _add_rul(df: pd.DataFrame) -> pd.DataFrame:
    """Add ``RUL`` column = failure_cycle - cycle, per engine."""
    failure_cycle = df.groupby("engine_id")["cycle"].transform("max")
    df = df.copy()
    df["RUL"] = (failure_cycle - df["cycle"]).astype("int32")
    return df


def _add_windowed_targets(df: pd.DataFrame, windows: Iterable[int]) -> pd.DataFrame:
    """Add ``y_<W>`` columns = (RUL <= W) as int8 for each W in ``windows``."""
    df = df.copy()
    for w in windows:
        df[f"y_{w}"] = (df["RUL"] <= int(w)).astype("int8")
    return df


def split_engines(
    df: pd.DataFrame,
    *,
    seed: int = DEFAULT_SEED,
    fractions: tuple[float, float, float] = DEFAULT_FRACTIONS,
    windows: Iterable[int] = DEFAULT_WINDOWS,
) -> Splits:
    """Engine-grouped split with RUL and binarized-target columns attached.

    Engines are shuffled with ``seed`` and partitioned by the cumulative
    ``fractions``. No engine appears in two splits. RUL and ``y_<W>``
    columns are added to all three splits so eval code can compute metrics
    uniformly.
    """
    if not np.isclose(sum(fractions), 1.0):
        raise ValueError(f"fractions must sum to 1.0, got {fractions} (sum={sum(fractions)})")

    rng = np.random.default_rng(seed)
    engines = df["engine_id"].drop_duplicates().to_numpy().copy()
    rng.shuffle(engines)

    n = len(engines)
    n_train = int(round(n * fractions[0]))
    n_test = int(round(n * fractions[1]))
    train_ids = set(engines[:n_train].tolist())
    test_ids = set(engines[n_train : n_train + n_test].tolist())
    val_ids = set(engines[n_train + n_test :].tolist())

    df = _add_rul(df)
    df = _add_windowed_targets(df, windows)

    train = df[df["engine_id"].isin(train_ids)].reset_index(drop=True)
    test = df[df["engine_id"].isin(test_ids)].reset_index(drop=True)
    validate = df[df["engine_id"].isin(val_ids)].reset_index(drop=True)

    return Splits(train=train, test=test, validate=validate)
