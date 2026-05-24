# Sandia talk — current state and resume recipe

Last updated: 2026-05-24 (active; pivoted from HAI to CMAPSS turbofan RUL).

## What this project is

Interview talk for David Dooling's in-person interview at Sandia National
Laboratories on **2026-06-11**. The deck has two halves under a single
thesis: *SHAP + named features + organizational primitives → not a black
box*.

- **Detection / RUL half (25 min)** — supervised LightGBM RUL classification
  on the NASA CMAPSS Turbofan Engine Degradation Simulation dataset
  (Saxena & Goebel 2008). Two classifiers per subset (failure windows 20
  and 50 cycles), Optuna-tuned, **native LightGBM SHAP** via
  `Booster.predict(X, pred_contrib=True)`. Realizes US patent
  11,742,934-B2 ("Method for Predictive Maintenance of Satellites").
- **LLM / Discovery half (15 min)** — OpenAlex literature → embeddings →
  UMAP → HDBSCAN → GPT-4o-mini SETA write-ups. Quantum tech-intel app at
  https://dooling-techintel-quantum.streamlit.app/.

## Pivot history

2026-05-22 → 2026-05-24: the original detection half used HAI ICS data +
self-healing IsolationForest + ruptures change-points. That work is
preserved under `archive_hai/` and replaced by the supervised CMAPSS RUL
pipeline. See the plan file
`~/.claude/plans/i-have-been-thiking-whimsical-snowflake.md`.

## NEXT SESSION — pick up here

**Phase 1 deliverable:** the orchestrator `python -m src.cmapss.artifacts`
exists and trains 8 LightGBM classifiers (4 subsets × 2 windows). Verify it
runs end-to-end and inspect the generated artifacts.

**After Phase 1 lands:**

- **Phase 2 — Streamlit app.** David will spec it then. Anticipated UI:
  per-engine P(class=1) over time (Plotly), click a point → waterfall SHAP
  for that (engine, cycle), HiPlot parallel-coords across engines.
  Dependencies to add: `hiplot`, `streamlit-plotly-events`.
- **Phase 3 — deck rework.** New `slides/sandia_talk_cmapss.tex`. Slides
  1, 2, 26-36 from the archived deck lift forward (LLM half + Sandia
  relevance + closer). Reword slide 1 patent framing
  (satellite-to-turbofan generalization).

## TL;DR resume recipe (fresh session)

```bash
cd /home/david/jobs/sandia_talk_hai
uv venv && source .venv/bin/activate
uv pip install -e .

# 1) Smoke test on FD001 only, 5 trials (fast, ~1 min):
uv run --active python -m src.cmapss.artifacts --subsets FD001 --n-trials 5

# 2) Full run: 4 subsets × 2 windows × 30 Optuna trials (~15-30 min):
uv run --active python -m src.cmapss.artifacts

# 3) Confirm artifacts:
ls models/                          # 8 .txt LightGBM boosters
ls eval/                            # predictions, SHAP, metrics_*.json
cat eval/metrics_FD001_w50.json     # one summary
```

## File layout

```
sandia_talk_hai/
├── archive_hai/                       HAI work, preserved (not deleted)
│   ├── src/  slides/  app/  artifacts/
├── data/
│   ├── hai/_repo/                     190 MB git clone, leave on disk
│   └── cmapss/                        ~6 MB, auto-downloaded
│       ├── train_FD001.txt … train_FD004.txt
│       ├── test_FD001.txt … RUL_FD004.txt
│       └── Damage Propagation Modeling.pdf
├── src/
│   ├── features.py                    generic drop_bad_columns + z-score
│   └── cmapss/
│       ├── load.py                    download + rename + datetime index
│       ├── split.py                   60/20/20 engine-grouped + RUL + y_W
│       ├── train.py                   Optuna + LightGBM + native SHAP
│       └── artifacts.py               orchestrator
├── models/                            8 .txt LightGBM boosters
├── eval/                              predictions + SHAP + metrics
├── slides/                            to be reworked in Phase 3
│   └── figures/openalex_screenshots/  LLM half, stays
├── pyproject.toml
├── STATUS.md
└── uv.lock
```

## Key design decisions

- **All four CMAPSS subsets (FD001–FD004).** One pipeline per subset; results
  reported per (subset, window) so a stakeholder can see the operating-
  condition / fault-mode complexity progression.
- **Per-cycle classification, not per-row regression.** Each row already
  represents one engine cycle in the source data; the binarized target
  `y_W = (RUL ≤ W)` is well-posed without windowing.
- **Two failure windows (W ∈ {20, 50})** capture two operational regimes:
  a tight late-warning model (W=20) and a broader early-warning model
  (W=50). Both are LightGBM binary classifiers with the same feature set.
- **Engine-grouped 60/20/20 split (seed=42).** No engine appears in two
  splits. The shipped `test_FDxxx.txt` files are *not* used in Phase 1
  (they are truncated runs without per-row failure times).
- **Optuna TPE, 30 trials, AUC-PR objective.** GroupKFold(5) on engine_id
  inside the trial. Refit best params on full train.
- **`is_unbalance=True`** in LightGBM to handle the heavy class imbalance,
  especially for W=20 (positive rate around 5-10% of cycles).
- **Native LightGBM SHAP.** Computed via `Booster.predict(X, pred_contrib=True)`
  for every test and validation row. **No `import shap` anywhere.**
- **Synthetic datetime index.** Cycle 1 = 2024-01-01 00:00:00, +1 hour per
  cycle. Cosmetic but it makes Plotly traces in Phase 2 legible and matches
  the "operational data" feel.
- **Renamed sensor columns** per Saxena/Goebel Table 1 (T2, T24, T30, T50,
  P2, P15, P30, Nf, Nc, epr, Ps30, phi, NRf, NRc, BPR, farB, htBleed,
  Nf_dmd, PCNfR_dmd, W31, W32 + altitude / mach_number / TRA).

## Notes

- The HAI work (self-healing IsolationForest, ruptures CPs, IQR fences) is
  archived intact under `archive_hai/`; nothing was deleted.
- `archive_hai/src/anomaly.py:441` is the original native-LightGBM SHAP
  call site; the new CMAPSS pipeline uses the same pattern in
  `src/cmapss/train.py:predict_with_shap`.
