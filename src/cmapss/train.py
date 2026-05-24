"""Optuna-tuned LightGBM binary classifier for CMAPSS RUL-window targets.

One classifier per (subset, failure_window) pair. The hyperparameters are
optimized with Optuna against an engine-grouped 5-fold CV objective
(AUC-PR), then refit on the full training split.

SHAP values are computed with the **native LightGBM** API
``Booster.predict(X, pred_contrib=True)`` — no external ``shap`` package.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import lightgbm as lgb
import numpy as np
import optuna
import pandas as pd
from sklearn.metrics import average_precision_score
from sklearn.model_selection import GroupKFold

optuna.logging.set_verbosity(optuna.logging.WARNING)


@dataclass
class TrainedModel:
    """A fitted LightGBM Booster plus the metadata needed to re-use it."""

    booster: lgb.Booster
    feature_names: list[str]
    target_name: str
    best_params: dict
    cv_auc_pr: float

    def save(self, path: str | Path) -> Path:
        """Save the booster as a native LightGBM text model."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.booster.save_model(str(path))
        return path


# ----------------------------------------------------------- Optuna objective

def _objective(
    trial: optuna.Trial,
    X: np.ndarray,
    y: np.ndarray,
    groups: np.ndarray,
    *,
    n_splits: int,
    seed: int,
) -> float:
    params = {
        "objective": "binary",
        "metric": "average_precision",
        "verbosity": -1,
        "feature_pre_filter": False,
        "is_unbalance": True,
        "seed": seed,
        "num_threads": 0,
        "num_leaves": trial.suggest_int("num_leaves", 15, 255),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "min_data_in_leaf": trial.suggest_int("min_data_in_leaf", 10, 200),
        "feature_fraction": trial.suggest_float("feature_fraction", 0.6, 1.0),
        "bagging_fraction": trial.suggest_float("bagging_fraction", 0.6, 1.0),
        "bagging_freq": 1,
    }
    n_estimators = trial.suggest_int("n_estimators", 100, 800)

    kf = GroupKFold(n_splits=n_splits)
    scores: list[float] = []
    for tr_idx, vl_idx in kf.split(X, y, groups=groups):
        # GroupKFold may produce a fold whose validation slice has zero
        # positives — AUC-PR is undefined there; skip those folds.
        if y[vl_idx].sum() == 0 or y[tr_idx].sum() == 0:
            continue
        dtrain = lgb.Dataset(X[tr_idx], label=y[tr_idx])
        booster = lgb.train(params, dtrain, num_boost_round=n_estimators)
        prob = booster.predict(X[vl_idx])
        scores.append(float(average_precision_score(y[vl_idx], prob)))
    if not scores:
        # All folds were degenerate (extreme imbalance). Give Optuna a
        # finite-but-bad value so it keeps exploring.
        return 0.0
    return float(np.mean(scores))


# ----------------------------------------------------------- public API

def train_window_classifier(
    train_df: pd.DataFrame,
    *,
    feature_names: Sequence[str],
    target_col: str,
    n_trials: int = 30,
    n_splits: int = 5,
    seed: int = 42,
) -> TrainedModel:
    """Tune + refit a LightGBM binary classifier on ``train_df``.

    ``train_df`` must include ``engine_id`` (for engine-grouped CV folds),
    ``target_col`` (the 0/1 RUL-window target), and the feature columns.
    """
    X = train_df[list(feature_names)].to_numpy(dtype=np.float32)
    y = train_df[target_col].to_numpy(dtype=np.int8)
    groups = train_df["engine_id"].to_numpy()

    sampler = optuna.samplers.TPESampler(seed=seed)
    study = optuna.create_study(direction="maximize", sampler=sampler)
    study.optimize(
        lambda t: _objective(t, X, y, groups, n_splits=n_splits, seed=seed),
        n_trials=n_trials,
        show_progress_bar=False,
    )

    best = dict(study.best_params)
    n_estimators = int(best.pop("n_estimators"))
    refit_params = {
        "objective": "binary",
        "metric": "average_precision",
        "verbosity": -1,
        "feature_pre_filter": False,
        "is_unbalance": True,
        "seed": seed,
        "num_threads": 0,
        "bagging_freq": 1,
        **best,
    }
    dtrain = lgb.Dataset(X, label=y, feature_name=list(feature_names))
    booster = lgb.train(refit_params, dtrain, num_boost_round=n_estimators)

    return TrainedModel(
        booster=booster,
        feature_names=list(feature_names),
        target_name=target_col,
        best_params={**refit_params, "n_estimators": n_estimators},
        cv_auc_pr=float(study.best_value),
    )


def predict_with_shap(
    model: TrainedModel,
    df: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Return (probabilities, shap_values, base_value).

    ``shap_values`` shape: ``(n_rows, n_features)``. ``base_value`` is the
    LightGBM intercept (log-odds), shared across rows.

    Uses LightGBM's native SHAP only: ``Booster.predict(X, pred_contrib=True)``.
    """
    X = df[model.feature_names].to_numpy(dtype=np.float32)
    prob = model.booster.predict(X)
    contribs = model.booster.predict(X, pred_contrib=True)
    contribs = np.asarray(contribs)
    shap_values = contribs[:, :-1]
    base_value = float(contribs[0, -1])
    return prob, shap_values, base_value
