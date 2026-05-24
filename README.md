# CMAPSS Turbofan RUL — LightGBM + native SHAP

Interactive dashboard for supervised remaining-useful-life (RUL) classification
on the NASA CMAPSS Turbofan Engine Degradation Simulation dataset
(Saxena & Goebel 2008).

For each of the four CMAPSS subsets (FD001–FD004) and two failure-window
thresholds (W ∈ {20, 50} cycles), a LightGBM binary classifier was
hyperparameter-tuned with Optuna (engine-grouped 5-fold CV, AUC-PR
objective). SHAP contributions are computed entirely via LightGBM's native
API — `Booster.predict(X, pred_contrib=True)` — with no `import shap` and
no external explainer dependency.

## What the app shows

- **Engine view + SHAP** — per-engine P(class=1) trajectory; click any
  cycle to see a signed-bar SHAP attribution for that exact moment. Below
  that, pick any feature from a dropdown (sorted by `|SHAP|` at the
  clicked cycle) and see its lifetime trace coloured red/blue by SHAP sign
  and sized by `|SHAP|`.
- **Global importance** — mean `|SHAP|` across every row in the chosen
  split, for the chosen (subset, window).
- **Run metadata** — best Optuna parameters, test/validate metric blocks,
  features used.

## Reproducing the pipeline

```bash
pip install -e .
python -m src.cmapss.artifacts          # 4 subsets x 2 windows, ~15-30 min
streamlit run app/streamlit_app.py
```

The CMAPSS dataset is auto-downloaded from a public S3 mirror on first
use; no API keys or secrets are required.

## Data citation

Saxena, A. and Goebel, K. (2008). "Turbofan Engine Degradation Simulation
Data Set", NASA Prognostics Data Repository, NASA Ames Research Center,
Moffett Field, CA.
