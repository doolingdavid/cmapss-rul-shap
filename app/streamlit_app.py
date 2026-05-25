"""Streamlit dashboard for the CMAPSS RUL pipeline.

Reads the artifacts produced by ``python -m src.cmapss.artifacts``:

    models/lgbm_FD00{1..4}_w{20,50}.txt
    eval/predictions_FD00{1..4}_w{20,50}.parquet
    eval/validation_predictions_FD00{1..4}_w{20,50}.parquet
    eval/shap_FD00{1..4}_w{20,50}.parquet
    eval/validation_shap_FD00{1..4}_w{20,50}.parquet
    eval/metrics_FD00{1..4}_w{20,50}.json

No model retraining happens here. All SHAP values were precomputed via the
native LightGBM API (``Booster.predict(X, pred_contrib=True)``).

Run:
    streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Literal

# Streamlit runs this file directly; ensure the project root (which holds
# the ``src`` package) is on sys.path before importing from it.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import lightgbm as lgb
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from src.cmapss.load import (
    download_cmapss as _download_cmapss,
    read_subset as _read_cmapss_subset,
)
from src.cmapss.split import split_engines as _split_engines

ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "models"
EVAL_DIR = ROOT / "eval"

SUBSETS = ("FD001", "FD002", "FD003", "FD004")
WINDOWS = (20, 50)
SPLITS = ("validate", "test")

# ---------------------------------------------------------------- cached IO

@st.cache_resource(show_spinner=False)
def load_booster(subset: str, window: int) -> lgb.Booster:
    return lgb.Booster(model_file=str(MODELS_DIR / f"lgbm_{subset}_w{window}.txt"))


@st.cache_data(show_spinner=False)
def load_predictions(subset: str, window: int, split: str) -> pd.DataFrame:
    fname = "predictions" if split == "test" else "validation_predictions"
    return pd.read_parquet(EVAL_DIR / f"{fname}_{subset}_w{window}.parquet")


@st.cache_data(show_spinner=False)
def load_shap(subset: str, window: int, split: str) -> pd.DataFrame:
    fname = "shap" if split == "test" else "validation_shap"
    return pd.read_parquet(EVAL_DIR / f"{fname}_{subset}_w{window}.parquet")


@st.cache_data(show_spinner=False)
def load_metrics(subset: str, window: int) -> dict:
    return json.loads((EVAL_DIR / f"metrics_{subset}_w{window}.json").read_text())


@st.cache_data(show_spinner="Loading raw sensor traces…")
def load_raw_features(subset: str) -> pd.DataFrame:
    """Raw (un-standardized) sensor and op-setting values per (engine, cycle).

    Reads directly from ``data/cmapss/train_FDxxx.txt`` so the feature
    values are in physical units (e.g. degrees Rankine, RPM, psia), not
    the z-scored values the model actually consumes.

    On a fresh Streamlit Cloud container the data directory is empty;
    ``download_cmapss`` fetches the ~6 MB CMAPSS zip from the public S3
    mirror on the first call and is a no-op thereafter.
    """
    data_dir = ROOT / "data" / "cmapss"
    if not (data_dir / f"train_{subset}.txt").exists():
        _download_cmapss(data_dir)
    return _read_cmapss_subset(subset, data_dir)


@st.cache_data(show_spinner="Reconstructing training split…")
def load_train_split(subset: str) -> pd.DataFrame:
    """The engine-grouped TRAIN split for ``subset`` in physical units, with
    ``RUL`` and ``y_20`` / ``y_50`` attached.

    Re-derives the *exact* deterministic split (seed=42, 60/20/20, grouped by
    engine) the boosters were trained on, so the parallel-coordinates
    background is the literal training data for the selected model. Values are
    in physical units rather than the z-scored inputs the booster consumes;
    z-scoring is an affine per-column map, which HiPlot's per-axis autoscaling
    renders identically — only the tick labels change (e.g. 1590 °R vs +1.8σ).
    """
    raw = load_raw_features(subset)
    return _split_engines(raw, seed=42, windows=WINDOWS).train.reset_index(drop=True)


@st.cache_data(show_spinner="Building parallel-coordinates view…")
def build_hiplot_html(
    subset: str,
    window: int,
    split: str,
    engine_id: int,
    clicked_cycle: int,
    n_axes: int,
    max_bg: int,
    seed: int = 42,
) -> str:
    """Render a HiPlot parallel-coordinates plot to a standalone HTML string.

    Background = the training-split rows for ``(subset, window)`` over the
    model's ``n_axes`` most important features (by global mean|SHAP|) plus
    RUL, colored by whether each row sits inside the failure window. The
    clicked (engine, cycle) is overlaid as a single near-black line so a
    reviewer can see it tracks the in-window cloud along the very sensors its
    SHAP bars flagged — the "no black box" argument, made visually.

    HiPlot does not embed cleanly as a native Streamlit chart; we serialize
    to HTML here and inject it with ``components.html`` at the call site.
    """
    import hiplot as hip  # lazy: keeps app cold-start light

    axes = _global_importance_order(subset, window, split)[: max(1, n_axes)]
    ycol = f"y_{window}"
    # ASCII-only category labels: HiPlot's frontend matches the colorby
    # values against the `colors`-map keys, and non-ASCII glyphs (≤, ·, ◆)
    # can round-trip inconsistently and silently disable the color scale.
    in_lab = f"RUL_le_{window}"
    out_lab = f"RUL_gt_{window}"
    sel_lab = "selected"

    train = load_train_split(subset)
    bg = train[axes + ["RUL", ycol]].copy()
    bg["group"] = np.where(bg[ycol].to_numpy() == 1, in_lab, out_lab)
    bg = bg.drop(columns=[ycol])
    # Stratified downsample by class so neither dominates and the cloud stays
    # translucent enough for the overlaid black line to read.
    if len(bg) > max_bg:
        bg = bg.groupby("group", group_keys=False).sample(
            frac=max_bg / len(bg), random_state=seed
        )

    # The clicked cycle, in the same physical units.
    raw = load_raw_features(subset)
    eng = raw.loc[raw["engine_id"] == engine_id]
    fail_cycle = int(eng["cycle"].max())
    srow = eng.loc[eng["cycle"] == clicked_cycle, axes].copy()
    srow["RUL"] = fail_cycle - int(clicked_cycle)
    srow["group"] = sel_lab

    plot_cols = axes + ["RUL", "group"]
    # Selected row last so it draws on top of the background cloud.
    df = pd.concat([bg[plot_cols], srow[plot_cols]], ignore_index=True)

    exp = hip.Experiment.from_dataframe(df)
    exp.colorby = "group"
    # Force the column categorical and let HiPlot's built-in palette assign
    # the three colors. An explicit `colors` map appears to suppress the
    # scale in this build (lines render all-black), so we rely on the palette
    # instead. The labels sort alphabetically RUL_gt < RUL_le < selected, so
    # the palette lands blue → out-of-window, orange → in-window, red →
    # selected (which still stands out). NB: in HiPlot's color menu the
    # active color axis renders *greyed* — that's the "currently selected"
    # marker, not "uncolorable".
    exp.parameters_definition["group"].type = hip.ValueType.CATEGORICAL
    # from_dataframe sets axis order = column order, but the parallel plot
    # lays axes out right-to-left, so the most-important feature ends up on
    # the right. Reverse the order list so it lands on the left.
    exp.display_data(hip.Displays.PARALLEL_PLOT)["order"] = list(reversed(plot_cols))
    return exp.to_html()


def _inject_thick_selected(html: str, width: int) -> str:
    """Make the lone ``selected`` line draw thick and fully opaque, on load.

    HiPlot has no per-line width API, and it dims non-highlighted lines by
    baking a *low alpha into the stroke color itself* (normal pass uses
    ``rgba(r,g,b,<low>)``; only its interactive highlight pass uses alpha 1 at
    width 4) — so the single clicked-cycle trace is both thin and nearly
    transparent. We monkeypatch the canvas 2D ``stroke()``: when the stroke
    color is red-dominant (the ``selected`` class — distinct from the
    blue/orange background) we redraw it at ``width`` px and force the color
    to *full opacity* (``globalAlpha`` is useless here because the alpha lives
    in the color). Crucially we also wrap ``getContext`` so the patch is
    installed before HiPlot's first paint, giving a thick trace on load
    without any interaction. The interval re-patches canvases made later.
    """
    script = """
<script>(function(){
  var W=%d;
  function rgbOf(s){s=(''+s).trim();var m=s.match(/^#?([0-9a-fA-F]{6})$/);
    if(m){var n=parseInt(m[1],16);return [(n>>16)&255,(n>>8)&255,n&255];}
    m=s.match(/rgba?\\(\\s*(\\d+)\\s*,\\s*(\\d+)\\s*,\\s*(\\d+)/);
    if(m){return [+m[1],+m[2],+m[3]];}return null;}
  function patch(ctx){if(!ctx||ctx.__hipThick)return;ctx.__hipThick=true;
    var os=ctx.stroke;
    ctx.stroke=function(){
      var c=rgbOf(this.strokeStyle);
      if(c&&c[0]>150&&c[1]<90&&c[2]<90){
        var lw=this.lineWidth,ss=this.strokeStyle;
        this.lineWidth=W;this.strokeStyle='rgb('+c[0]+','+c[1]+','+c[2]+')';
        os.apply(this,arguments);
        this.lineWidth=lw;this.strokeStyle=ss;
      }else{os.apply(this,arguments);}
    };}
  var og=HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext=function(t){var ctx=og.apply(this,arguments);
    if(t==='2d'){try{patch(ctx);}catch(e){}}return ctx;};
  setInterval(function(){var cs=document.getElementsByTagName('canvas');
    for(var i=0;i<cs.length;i++){try{patch(cs[i].getContext('2d'));}catch(e){}}},400);
})();</script>
""" % int(width)
    if "</body>" in html:
        return html.replace("</body>", script + "</body>", 1)
    return html + script


# ---------------------------------------------------------------- helpers

def _feature_names_from_shap(shap_df: pd.DataFrame) -> list[str]:
    return [c[len("shap__"):] for c in shap_df.columns if c.startswith("shap__")]


def _global_importance_order(subset: str, window: int, split: str) -> list[str]:
    """Model feature names ordered by descending global mean(|SHAP|)."""
    shap_df = load_shap(subset, window, split)
    feats = _feature_names_from_shap(shap_df)
    mean_abs = shap_df[[f"shap__{f}" for f in feats]].abs().mean()
    mean_abs.index = feats
    return mean_abs.sort_values(ascending=False).index.tolist()


def _engine_subset(df: pd.DataFrame, engine_id: int) -> pd.DataFrame:
    return df.loc[df["engine_id"] == engine_id].sort_values("cycle").reset_index(drop=True)


# ---------------------------------------------------------------- plots

def _trajectory_figure(
    engine_pred: pd.DataFrame,
    window: int,
    selected_cycle: int | None,
) -> go.Figure:
    """P(class=1) over cycles, with y_true shading.  The clickable points
    expose cycle / RUL / y_true on hover.
    """
    fig = go.Figure()

    pos_mask = engine_pred["y_true"].to_numpy() == 1
    if pos_mask.any():
        first = int(engine_pred.loc[pos_mask, "cycle"].min())
        last = int(engine_pred.loc[pos_mask, "cycle"].max())
        fig.add_vrect(
            x0=first - 0.5, x1=last + 0.5,
            fillcolor="rgba(220, 60, 60, 0.12)",
            line_width=0,
            annotation_text=f"y_true = 1 (RUL ≤ {window})",
            annotation_position="top left",
            annotation=dict(font=dict(color="rgb(180,60,60)")),
        )

    fig.add_trace(
        go.Scatter(
            x=engine_pred["cycle"],
            y=engine_pred["predicted_prob"],
            mode="lines+markers",
            name=f"P(RUL ≤ {window})",
            marker=dict(size=6, color="rgb(40, 90, 160)"),
            line=dict(color="rgb(40, 90, 160)", width=2),
            customdata=engine_pred[["cycle", "RUL", "y_true"]].to_numpy(),
            hovertemplate=(
                "cycle %{customdata[0]}<br>"
                "P=%{y:.3f}<br>"
                "RUL=%{customdata[1]}<br>"
                "y_true=%{customdata[2]}<extra></extra>"
            ),
        )
    )

    if selected_cycle is not None and selected_cycle in engine_pred["cycle"].values:
        row = engine_pred.loc[engine_pred["cycle"] == selected_cycle].iloc[0]
        fig.add_trace(
            go.Scatter(
                x=[row["cycle"]],
                y=[row["predicted_prob"]],
                mode="markers",
                marker=dict(size=14, color="rgb(255, 140, 0)",
                            line=dict(color="black", width=1.5)),
                name=f"selected (cycle {int(row['cycle'])})",
                hoverinfo="skip",
            )
        )

    fig.add_hline(y=0.5, line_dash="dot", line_color="rgba(0,0,0,0.3)",
                  annotation_text="P=0.5", annotation_position="bottom right")

    fig.update_layout(
        height=420,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", y=1.08, x=0),
        hovermode="closest",
        clickmode="event+select",
        xaxis_title="cycle",
        yaxis_title="P(class=1)",
        yaxis_range=[0, 1.02],
    )
    return fig


def _waterfall_figure(
    shap_row: pd.Series,
    feature_names: list[str],
    base_value: float,
    predicted_prob: float,
    top_k: int = 12,
) -> go.Figure:
    """Signed SHAP-contribution bar chart for a single (engine, cycle) row.

    Each bar starts at x=0:
      - **Red, pointing right**: feature pushes the prediction toward class 1
        (positive SHAP, i.e. raises the log-odds).
      - **Blue, pointing left**: feature pushes toward class 0
        (negative SHAP, i.e. lowers the log-odds).

    Top-K features by absolute contribution; sum of remaining features is
    shown as a single bar at the bottom. Base log-odds and final
    probability are captured in the title.
    """
    contribs = pd.Series(
        {f: float(shap_row[f"shap__{f}"]) for f in feature_names}
    )
    ranked = contribs.reindex(contribs.abs().sort_values(ascending=False).index)
    top = ranked.head(top_k)
    others_sum = float(ranked.iloc[top_k:].sum())

    labels = list(top.index)
    values = list(top.values)
    if abs(others_sum) > 1e-6:
        labels.append(f"… {len(ranked) - top_k} other features (sum)")
        values.append(others_sum)

    colors = ["rgb(200, 60, 60)" if v > 0 else "rgb(60, 110, 175)" for v in values]
    final_logit = base_value + float(contribs.sum())

    fig = go.Figure(
        go.Bar(
            orientation="h",
            x=values,
            y=labels,
            marker=dict(color=colors, line=dict(color="rgba(0,0,0,0.25)", width=0.5)),
            text=[f"{v:+.3f}" for v in values],
            textposition="outside",
            hovertemplate="%{y}<br>SHAP = %{x:+.4f}<extra></extra>",
        )
    )
    fig.add_vline(x=0, line_color="black", line_width=1)
    fig.update_layout(
        height=520,
        margin=dict(l=10, r=10, t=50, b=10),
        title=dict(
            text=(
                f"base logit = {base_value:+.3f} → final logit "
                f"{final_logit:+.3f} → P(class=1) = {predicted_prob:.3f}"
            ),
            x=0.5, xanchor="center", font=dict(size=13),
        ),
        xaxis_title="SHAP contribution (log-odds units)",
        yaxis=dict(autorange="reversed"),
        showlegend=False,
        bargap=0.25,
    )
    return fig


def _feature_timeseries_figure(
    engine_raw: pd.DataFrame,
    engine_shap: pd.DataFrame,
    feature: str,
    clicked_cycle: int,
    window: int,
) -> go.Figure:
    """Time series of a single feature over an engine's life, with each
    point colored by sign of its SHAP value and sized by ``|SHAP|``.

    Red marker = this feature pushed P(class=1) up at that cycle.
    Blue marker = this feature pushed P(class=1) down.
    Marker area is proportional to ``|SHAP|`` for that cycle.
    """
    merged = (
        engine_raw[["cycle", feature]]
        .merge(
            engine_shap[["cycle", f"shap__{feature}", "RUL"]],
            on="cycle", how="inner",
        )
        .sort_values("cycle")
        .reset_index(drop=True)
    )
    shap_col = f"shap__{feature}"
    abs_shap = merged[shap_col].abs()
    max_abs = float(abs_shap.max()) if len(abs_shap) and abs_shap.max() > 0 else 1.0
    # Scale to a pleasant pixel range
    sizes = (4.0 + 22.0 * (abs_shap / max_abs)).clip(lower=4.0).to_numpy()
    colors = [
        "rgb(200, 60, 60)" if v > 0 else ("rgb(60, 110, 175)" if v < 0 else "rgb(150,150,150)")
        for v in merged[shap_col]
    ]

    fig = go.Figure()
    # Thin connecting line for trend readability
    fig.add_trace(
        go.Scatter(
            x=merged["cycle"], y=merged[feature],
            mode="lines",
            line=dict(color="rgba(0,0,0,0.18)", width=1),
            hoverinfo="skip",
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=merged["cycle"], y=merged[feature],
            mode="markers",
            marker=dict(
                size=sizes, color=colors,
                line=dict(color="rgba(0,0,0,0.35)", width=0.6),
                opacity=0.92,
            ),
            customdata=np.stack(
                [merged[shap_col].to_numpy(), merged["RUL"].to_numpy()], axis=-1
            ),
            hovertemplate=(
                f"cycle %{{x}}<br>{feature} = %{{y}}<br>"
                "SHAP = %{customdata[0]:+.3f}<br>RUL = %{customdata[1]}<extra></extra>"
            ),
            showlegend=False,
        )
    )
    # Outline the clicked cycle
    if clicked_cycle in merged["cycle"].values:
        cr = merged.loc[merged["cycle"] == clicked_cycle].iloc[0]
        fig.add_trace(
            go.Scatter(
                x=[cr["cycle"]], y=[cr[feature]],
                mode="markers",
                marker=dict(size=24, color="rgba(0,0,0,0)",
                            line=dict(color="rgb(255,140,0)", width=3)),
                hoverinfo="skip",
                name=f"selected cycle {int(cr['cycle'])}",
                showlegend=False,
            )
        )

    fig.update_layout(
        height=380,
        margin=dict(l=10, r=10, t=44, b=10),
        title=dict(
            text=(
                f"<b>{feature}</b> over engine lifetime — marker color = sign of SHAP "
                f"(red = pushes P(RUL≤{window}) up; blue = pushes down), "
                f"size ∝ |SHAP|"
            ),
            x=0.0, xanchor="left", font=dict(size=13),
        ),
        xaxis_title="cycle",
        yaxis_title=feature,
        hovermode="closest",
    )
    return fig


def _global_importance_figure(shap_df: pd.DataFrame, top_k: int = 20) -> go.Figure:
    feats = _feature_names_from_shap(shap_df)
    mean_abs = (
        shap_df[[f"shap__{f}" for f in feats]]
        .abs()
        .mean()
        .rename(lambda s: s[len("shap__"):])
        .sort_values(ascending=True)
    )
    top = mean_abs.tail(top_k)
    fig = go.Figure(
        go.Bar(
            x=top.values, y=top.index, orientation="h",
            marker_color="rgb(70, 130, 180)",
            text=[f"{v:.3f}" for v in top.values], textposition="outside",
        )
    )
    fig.update_layout(
        height=max(360, 22 * len(top)),
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title="mean(|SHAP|) over all rows in split  (log-odds units)",
        yaxis_title=None,
    )
    return fig


# ---------------------------------------------------------------- UI

st.set_page_config(
    page_title="CMAPSS RUL — LightGBM + native SHAP",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("CMAPSS Turbofan RUL — LightGBM classifier + native SHAP")
st.caption(
    "Saxena & Goebel 2008. Two binary RUL-window classifiers per subset "
    "(W=20, W=50). All SHAP values computed via "
    "`Booster.predict(X, pred_contrib=True)`."
)

with st.sidebar:
    st.header("Selection")
    subset = st.selectbox("Subset", SUBSETS, index=0)
    window = st.selectbox("Failure window (cycles)", WINDOWS, index=1)
    split = st.selectbox("Split", SPLITS, index=0,
                         help="`validate` = engines the HPO process never touched. "
                              "`test` = the held-out 20% used during pipeline dev.")

pred_df = load_predictions(subset, window, split)
shap_df = load_shap(subset, window, split)
metrics = load_metrics(subset, window)
feat_names = _feature_names_from_shap(shap_df)

split_metrics = metrics["validate" if split == "validate" else "test"]

# ---------------- sidebar engine selector
with st.sidebar:
    engines = sorted(pred_df["engine_id"].unique().tolist())
    # default to engine with the highest peak prob (most "interesting" trajectory)
    default_engine = int(pred_df.loc[pred_df["predicted_prob"].idxmax(), "engine_id"])
    default_idx = engines.index(default_engine)
    engine_id = st.selectbox("Engine", engines, index=default_idx)

    st.markdown("---")
    st.markdown(f"**Split-level metrics ({split})**")
    st.metric("AUC-PR", f"{split_metrics.get('auc_pr', float('nan')):.3f}")
    st.metric("ROC-AUC", f"{split_metrics.get('roc_auc', float('nan')):.3f}")
    st.caption(
        f"positive rate: {split_metrics.get('positive_rate', float('nan')):.3f} "
        f"• n={split_metrics.get('n', 0):,} • positives={split_metrics.get('positives', 0):,}"
    )

# ---------------- tabs

tab_engine, tab_global, tab_run = st.tabs(
    ["Engine view + SHAP", "Global importance", "Run metadata"]
)

# === Tab 1: per-engine trajectory + click-to-SHAP ============================
with tab_engine:
    engine_pred = _engine_subset(pred_df, engine_id)
    engine_shap = _engine_subset(shap_df, engine_id)

    # Default selected cycle = the engine's peak-probability cycle
    default_cycle = int(engine_pred.loc[engine_pred["predicted_prob"].idxmax(), "cycle"])

    st.subheader(
        f"Engine {engine_id} — {subset}, W={window}, split={split}  "
        f"(failed at cycle {int(engine_pred['cycle'].max())})"
    )
    st.caption(
        "Click any point on the trace to see the SHAP waterfall for that cycle. "
        "Red shading is where the true label `y_true=1` (i.e. RUL was actually ≤ W)."
    )

    fig_traj = _trajectory_figure(engine_pred, window, default_cycle)
    event = st.plotly_chart(
        fig_traj,
        on_select="rerun",
        key=f"traj_{subset}_{window}_{split}_{engine_id}",
        selection_mode=("points",),
    )

    # Resolve clicked cycle. The x-axis of the P(class=1) trace IS the cycle,
    # so we read straight from pts[0]["x"] and only fall back to customdata
    # if needed. (Streamlit's plotly event serializes customdata as a dict
    # keyed by column index, so cd[0] would raise KeyError on a list-style
    # access.)
    clicked_cycle = default_cycle
    sel = (event or {}).get("selection") if isinstance(event, dict) else None
    pts = (sel or {}).get("points") or []
    if pts:
        pt = pts[0]
        if pt.get("x") is not None:
            try:
                clicked_cycle = int(pt["x"])
            except (TypeError, ValueError):
                pass
        else:
            cd = pt.get("customdata")
            if isinstance(cd, dict) and 0 in cd:
                clicked_cycle = int(cd[0])
            elif isinstance(cd, (list, tuple)) and cd:
                clicked_cycle = int(cd[0])

    # SHAP for the clicked row
    shap_row = engine_shap.loc[engine_shap["cycle"] == clicked_cycle]
    if shap_row.empty:
        st.info(f"No SHAP row at cycle {clicked_cycle}; using default cycle {default_cycle}.")
        clicked_cycle = default_cycle
        shap_row = engine_shap.loc[engine_shap["cycle"] == default_cycle]

    shap_row = shap_row.iloc[0]
    pred_row = engine_pred.loc[engine_pred["cycle"] == clicked_cycle].iloc[0]

    cols = st.columns([2, 1])
    with cols[0]:
        st.markdown(
            f"**SHAP waterfall** — engine {engine_id}, cycle {clicked_cycle}, "
            f"RUL={int(pred_row['RUL'])}, P={float(pred_row['predicted_prob']):.3f}, "
            f"y_true={int(pred_row['y_true'])}"
        )
        fig_wf = _waterfall_figure(
            shap_row, feat_names,
            base_value=float(shap_row["base_value"]),
            predicted_prob=float(pred_row["predicted_prob"]),
        )
        st.plotly_chart(fig_wf, use_container_width=True)
    with cols[1]:
        st.markdown("**Top contributors (signed)**")
        contribs = pd.Series(
            {f: float(shap_row[f"shap__{f}"]) for f in feat_names},
            name="shap",
        )
        contribs = contribs.reindex(contribs.abs().sort_values(ascending=False).index)
        st.dataframe(
            contribs.head(15).rename("SHAP (log-odds)").to_frame().style.format("{:+.3f}"),
            use_container_width=True,
            height=520,
        )

    # --- Drill into one sensor's lifetime with SHAP-tinted markers -----------
    st.markdown("---")
    st.markdown(
        "### Sensor drill-down — pick a feature, see its lifetime trace"
    )
    st.caption(
        f"Features below are sorted by **|SHAP| at the clicked cycle "
        f"(cycle {clicked_cycle})** — the features the model leaned on hardest "
        "for *this* point. Pick one to see how it actually evolved over the "
        "engine's life; each marker is colored by the sign of its SHAP at "
        "that cycle and sized by |SHAP|."
    )
    ranked_feats = (
        contribs.abs().sort_values(ascending=False).index.tolist()
    )
    ranked_labels = [
        f"{f}    (|SHAP| = {abs(float(contribs[f])):.3f}, "
        f"{'+' if contribs[f] >= 0 else '−'})"
        for f in ranked_feats
    ]
    label_to_feat = dict(zip(ranked_labels, ranked_feats))
    chosen_label = st.selectbox(
        "Feature (sorted by |SHAP| at clicked cycle):",
        ranked_labels,
        index=0,
        key=f"feat_pick_{subset}_{window}_{split}_{engine_id}_{clicked_cycle}",
    )
    chosen_feat = label_to_feat[chosen_label]

    raw = load_raw_features(subset)
    engine_raw = _engine_subset(raw, engine_id)
    if chosen_feat not in engine_raw.columns:
        st.warning(
            f"Feature {chosen_feat!r} was dropped during preprocessing for "
            f"{subset} and has no raw trace to display."
        )
    else:
        fig_feat = _feature_timeseries_figure(
            engine_raw, engine_shap, chosen_feat, clicked_cycle, window
        )
        st.plotly_chart(fig_feat, use_container_width=True)

    # --- Parallel coordinates: this cycle against the training cloud ---------
    st.markdown("---")
    st.markdown("### Where this cycle sits in the training data (HiPlot)")
    st.caption(
        f"Each thin line is one **training-split** row for *{subset}* over the "
        "model's input features (physical units) plus RUL, colored by window "
        f"membership: **blue** = `RUL_gt_{window}` (out), **orange** = "
        f"`RUL_le_{window}` (in-window), and **red** = the **`selected`** "
        "cycle you clicked above (see the color legend in the plot). If "
        "LightGBM weren't a black box but merely organizing the named sensors, "
        "the clicked cycle should track the in-window cloud along exactly the "
        "axes its SHAP waterfall flagged. Drag on any axis to brush; reorder "
        "axes by dragging their labels."
    )
    _all_feats = _global_importance_order(subset, window, split)
    hc1, hc2, hc3 = st.columns(3)
    with hc1:
        n_axes = st.slider(
            "Feature axes shown (most important first)",
            min_value=4, max_value=len(_all_feats),
            value=min(12, len(_all_feats)),
            key=f"hip_axes_{subset}_{window}_{split}",
        )
    with hc2:
        max_bg = st.select_slider(
            "Max training rows drawn",
            options=[500, 1000, 1500, 2500, 4000],
            value=1500,
            key=f"hip_bg_{subset}_{window}_{split}",
        )
    with hc3:
        sel_width = st.slider(
            "Selected line width (px)",
            min_value=1, max_value=24, value=11,
            key=f"hip_w_{subset}_{window}_{split}",
        )
    hip_html = build_hiplot_html(
        subset, window, split, int(engine_id), int(clicked_cycle),
        int(n_axes), int(max_bg),
    )
    hip_html = _inject_thick_selected(hip_html, int(sel_width))
    components.html(hip_html, height=680, scrolling=True)

# === Tab 2: Global importance ================================================
with tab_global:
    st.subheader(f"Global feature importance — {subset}, W={window}, split={split}")
    st.caption(
        "Mean of |SHAP| over every row in the split. "
        "Bars rank features by how much they actually shifted predictions "
        "(in log-odds units). This is what the model believes matters."
    )
    fig_gi = _global_importance_figure(shap_df, top_k=20)
    st.plotly_chart(fig_gi, use_container_width=True)

    with st.expander("Raw table"):
        feats = _feature_names_from_shap(shap_df)
        mean_abs = (
            shap_df[[f"shap__{f}" for f in feats]]
            .abs()
            .mean()
            .rename(lambda s: s[len("shap__"):])
            .sort_values(ascending=False)
            .rename("mean(|SHAP|)")
            .to_frame()
        )
        st.dataframe(mean_abs.style.format("{:.4f}"), use_container_width=True)

# === Tab 3: Run metadata =====================================================
with tab_run:
    st.subheader(f"Run metadata — {subset}, W={window}")
    cols = st.columns(2)
    with cols[0]:
        st.markdown("**Best Optuna parameters**")
        st.json(metrics["best_params"])
    with cols[1]:
        st.markdown("**Test metrics**")
        st.json(metrics["test"])
        st.markdown("**Validation metrics**")
        st.json(metrics["validate"])
    st.markdown(f"**CV objective (AUC-PR, 5-fold engine-grouped):** {metrics['cv_auc_pr']:.4f}")
    st.markdown(f"**Features used ({len(metrics['features'])}):**")
    st.code(", ".join(metrics["features"]), language=None)
