# Sandia talk — current state and resume recipe

Last updated: 2026-05-31 (see "## 2026-05-31 session" below for the latest
work: 3 new slides → deck now **33 frames**, gpt-5.4-mini app migration shipped
live, quantum screenshots re-captured). CMAPSS pivot landed 2026-05-24;
HiPlot parallel-coordinates view added + deployed 2026-05-25; deck
restructured (basics + Optuna slides added; global/differential-SHAP and
hypersonics slides removed; techintel screenshots cropped). Latest app
commit: `07569cb`. Deck now **30 frames** (2026-05-26: metric-definitions
slide added before the performance table; multi-window causal-chain bridge
slide added at the end of the CMAPSS half; **5-frame OSINT case-study module**
added to the techintel half after the quantum screenshots — see note below.
2026-05-28: **2-frame unsupervised coda** added at the end of the CMAPSS half
— see "Unsupervised damage-evolution coda" below. It is **additive**: David
decided 2026-05-28 to **keep the OSINT module** (do NOT drop it), so the deck
carries both).
At **33 frames** the deck runs ~65 min at 2 min/slide; **needs a trim pass** to
fit the 45-min slot — trim elsewhere (quantum q01–q05), the OSINT module stays.

## 2026-05-31 session

**Three new slides added** (deck 30 → 33 frames). Build scripts live under the
gitignored `slides/` tree (local-only, like the rest of the deck):

1. **"Why 30 trials? — the same floor, measured (Monte-Carlo)"** (after the
   order-statistics slide). Empirical proof that best-of-30 lands in the top 5%
   ~78.5% of the time; distribution-free across Normal/Uniform/Exponential.
   Script `slides/cmapss/build_order_stats.py` → `figures/order_stats_proof.png`.
2. **"The signal behind the map — what ruptures actually sees (FD001 #9)"**
   (after the unsupervised heatmap). The `rpt.display(signal, bkps)` view —
   stacked z-scored channels, alternating segment bands, changepoint lines —
   imports build_unsupervised's pipeline so the segmentation is identical to the
   heatmap. Script `slides/cmapss/build_ruptures_signal.py` →
   `figures/ruptures_signal_FD001.png`.
3. **"The magic — the corpus classifies itself"** (after the Pipeline table).
   Flow (title+abstract → all-MiniLM-L6-v2 → 384-dim → UMAP) feeding a real
   before→after scatter (24,359 papers → 148 HDBSCAN clusters, 30% noise
   dropped); PACS→PhySH "no librarian can do this" callout. Script
   `slides/build_pipeline_magic.py` → `figures/pipeline_magic.png` (reads
   `~/jobs/openalex_local/techintel-quantum/updatejammingdfinfo2d.pkl.gz`).
   **Also fixed slide 17** counts: ~3,000/11 clusters → **~24,000 papers / 148
   clusters** (matches the q01 screenshot + live app).

**App: gpt-4o-mini → gpt-5.4-mini, SHIPPED LIVE.** The techintel-quantum SETA
app was migrated and deployed (commits `e4dcbed`, `b89a8a5` on
`github.com/doolingdavid/techintel-quantum-talk` main). Also fixed a tab-stall
perf bug. Full details + gotchas in memory `[[techintel-gpt54mini-migration]]`.

**Quantum screenshots re-captured** from the upgraded live app into
`slides/figures/openalex_screenshots/`: `q01_scatter.png` (orientation now
matches live), `q02_writeup.png` (cropped to the dual-use payoff; full capture
preserved as `q02_writeup_fullpage.png`), `q05_article_writeup.png` (new
gpt-5.4-mini text); q03/q04 optional (data-only, unchanged). The q02 caption was
updated to gpt-5.4-mini / abstracts / ~$0.03.

**STILL OPEN from this session:** flip the remaining **"GPT-4o-mini"** mentions
to **gpt-5.4-mini** on slides **17, 19 (pipeline table stage E), 23 (q05
caption), 32 (portfolio)** — slide 22's q02 caption is already done. Also: the
**PPTX image backup** (`slides/sandia_talk_cmapss.pptx`) is stale at 30 slides —
regenerate via `python slides/build_talk_pptx.py` once edits settle.

## Interview

In-person at **Sandia National Laboratories on 2026-06-11**. 45-minute
technical talk. Unifying thesis: *SHAP + named features + organizational
primitives → ML/AI is not a black box.*

## What's landed

| Artifact | Path | State |
|---|---|---|
| **Live app** | https://dooling-cmapss-rul.streamlit.app/ | Deployed 2026-05-24 |
| **App repo** | https://github.com/doolingdavid/cmapss-rul-shap | Public, last commit `07569cb`; deploys from `main` |
| **App source** | `app/streamlit_app.py` | 3 tabs (Engine view + SHAP, Global importance, Run metadata) |
| **HiPlot view** | `app/streamlit_app.py` (engine tab) | Parallel-coordinates of training split + clicked-cycle overlay; deployed `a311c21` |
| **Trained models** | `models/lgbm_FD00{1..4}_w{20,50}.txt` | 8 LightGBM boosters, AUC-PR 0.91–0.96 on validation |
| **Eval artifacts** | `eval/*.parquet`, `eval/metrics_*.json` | Predictions + native-SHAP for test and validate splits |
| **Main 45-min deck** | `slides/sandia_talk_cmapss.tex` → `.pdf` | 28 frames (`slides/` is gitignored — local only) |
| **Deck figures** | `slides/cmapss/figures/`, `slides/figures/openalex_screenshots/` | Optuna: `build_optuna.py`; RUL+analogy: `build_basics.py`; HiPlot: `hiplot_view.png`; cropped techintel: `q0*_*.png`; global-SHAP (now unused): `build_phase3.py` |
| **Unsupervised coda** | `slides/cmapss/build_unsupervised.py` → `figures/unsupervised_heatmap.{png,html}` | Purely-unsupervised damage-evolution heatmap (see section below). PNG for the deck, HTML for interactive hover. Needs `vl-convert-python` (local venv only). |
| **Walkthrough deck** | `slides/app_walkthrough.pptx` | 24 slides, PowerPoint, generated by `slides/build_walkthrough_pptx.py` |
| **PPTX backup of talk** | `slides/sandia_talk_cmapss.pptx` | 30 slides, one full-bleed image per slide (pixel copy of the Beamer PDF). Non-editable venue fallback. Regenerate after any deck change: `slides/build_talk_pptx.py` (renders the PDF → 16:9 PPTX via PyMuPDF + python-pptx). |

## HiPlot parallel-coordinates view (added 2026-05-25)

In the **Engine view + SHAP** tab, clicking a cycle now also renders a HiPlot
parallel-coordinates plot (generated to HTML, embedded via
`components.html`). Each thin line is one **training-split** row for the
selected `(subset, window)` over the model's features (physical units) plus
RUL, colored by failure-window membership; the clicked cycle is overlaid as
a thick, full-opacity red trace. This makes the "no black box — LightGBM
just organizes the named sensors" thesis visually verifiable: the clicked
cycle should track the in-window cloud along the same axes its SHAP waterfall
flagged. Three sliders: axis count, background row cap, selected line width.

Hard-won implementation gotchas (all documented inline in
`app/streamlit_app.py`; **don't regress these**):

- **Axes are ordered by |SHAP| at the clicked cycle**, not global mean|SHAP|,
  so the leftmost axis matches the top of the waterfall (commit `a311c21`).
- **No explicit HiPlot `colors` map** — it silently disables the categorical
  color scale (all-black lines). Use the built-in palette; the ASCII labels
  `RUL_gt_W` / `RUL_le_W` / `selected` sort so the palette lands
  blue / orange / red.
- **Thick selected line = a canvas `stroke()` monkeypatch** injected into the
  HTML. HiPlot has no per-line width API and bakes opacity into the stroke
  *color* (not `globalAlpha`), so the patch forces full-opacity color + width
  and wraps `getContext` so it applies on first paint.
- **`streamlit` pinned `<1.58`** in `requirements.txt`/`pyproject.toml` to
  keep `components.v1.html` (flagged for removal after 2026-06-01).
- `hiplot>=0.1.33` added as a dependency.

## Unsupervised damage-evolution coda (added 2026-05-28)

Two frames at the **end of the CMAPSS half** (`cmapss/cmapss_block.tex`,
labelled frames 7–8), placed after the multi-window causal-chain bridge so the
coda **bridges into the unsupervised discovery (techintel) half**. **Additive
— the OSINT module stays** (David decided 2026-05-28 to keep OSINT; the coda
was floated as a possible OSINT replacement but he chose to keep both).

The point: drop all supervision. *"Imagine one engine arrives with nothing but
its telemetry — no failure time, no model. What does the data alone say?"*
Pipeline in `slides/cmapss/build_unsupervised.py`, per engine:

1. **Healthy-baseline z-score** — standardize each sensor against that engine's
   own first 25% of life (`HEALTHY_FRAC`). Early life ≈ 0; drift = damage. The
   healthy std is **floored at 10% of the sensor's lifetime std** so a near-flat
   sensor's noise can't explode into huge z and dominate (this tamed a spurious
   deep-red Nc/NRc in FD001).
2. **Regime-normalize the 6-condition subsets** (FD002/FD004 only) — KMeans
   (k=6) on the 3 operating settings, then healthy stats *within regime*, so
   operating-point swings don't masquerade as damage. Still 100% unsupervised.
3. **ruptures RBF changepoints** — `KernelCPD(kernel="rbf")`, automatic # of
   breaks via `pen=3.0`, `min_size = n//25`. Segments the life where behaviour
   shifts; segment counts came out 7/4/5/4 for the four examples.
4. **Altair heatmap** — cycle (variable-width segment rects) on x, 15 named
   sensors on y (grouped fan→core→turbine→bleed), each cell colored by mean
   z-score. Diverging `redblue` (reversed) scale, shared color cap clamped to
   ±6 z. Dashed rules mark the changepoints.

**Four worked examples**, one **median-lifetime validation engine** per subset
(seed-42 split): FD001 #9, FD002 #111, FD003 #14, FD004 #137 (all ~200–225
cycles so the 2×2 grid reads at one scale). Physics checks out — FD001 (HPC
fault) reddens Nc/T50 while Ps30 drifts, the textbook HPC-degradation signature,
with no label.

**Two outputs** (both in `slides/cmapss/figures/`, gitignored/local):
`unsupervised_heatmap.png` (no embedded title — Beamer frame title + caption
carry it; larger panels) for the deck, and `unsupervised_heatmap.html`
(titled + **interactive hover tooltips**) for exploration / Q&A.

**Dependency:** Altair static PNG export needs `vl-convert-python`. It is
installed in the **local `.venv` only** — *not* added to `pyproject.toml` /
`requirements.txt` / `uv.lock`, because the deck build is local and the
deployed Streamlit app must not pull it in. If `build_unsupervised.py` errors
with "no PNG export engine," run `uv pip install vl-convert-python` in the venv.

Rebuild: `python slides/cmapss/build_unsupervised.py`, then recompile the deck.

## Resume in a fresh Claude session

```bash
cd /home/david/jobs/sandia_talk_hai
```

Open a new Claude Code session and say *"resuming Sandia talk work, what's
the state?"* Memory will auto-load and the assistant will read this file.

To re-run anything locally:
```bash
source .venv/bin/activate

# Refit the 8 models from scratch (~15-30 min):
python -m src.cmapss.artifacts

# Rebuild deck figures (~5 s each):
python slides/cmapss/build_phase3.py       # global-SHAP panel (currently unused)
python slides/cmapss/build_optuna.py       # Optuna TPE search keyframes
python slides/cmapss/build_basics.py       # RUL-label + tree-line analogy
python slides/cmapss/build_unsupervised.py # unsupervised changepoint heatmap (.png + .html)

# Rebuild the walkthrough .pptx (~1 s):
python slides/build_walkthrough_pptx.py

# Rebuild the Beamer deck:
cd slides && pdflatex -interaction=nonstopmode sandia_talk_cmapss.tex \
  && pdflatex -interaction=nonstopmode sandia_talk_cmapss.tex

# Launch the dashboard locally:
streamlit run app/streamlit_app.py --server.port 8765
```

To re-deploy the app, push to `main` — Streamlit Cloud auto-redeploys.
**CRITICAL deploy gotcha:** Streamlit Cloud installs from `uv.lock` (uv-sync),
which takes precedence over `requirements.txt` / `pyproject.toml`. After ANY
dependency change you MUST run `uv lock` and commit the updated lock, or the
deploy crashes (this bit us: `ModuleNotFoundError: No module named 'hiplot'`,
fixed in `07569cb`).

## Pivot history (for context)

2026-05-22 → 2026-05-24: original detection half used HAI ICS data +
self-healing IsolationForest. Pivoted to supervised CMAPSS RUL +
LightGBM + native SHAP. Original HAI work archived at
`archive_hai/` — preserved, not deleted.

Phase 4 (DTW + UMAP cohort view) was built then **removed 2026-05-24**
because David judged it distracting for a 45-min talk. Implementation
preserved in git history at commit `4eef414` of the cmapss-rul-shap
repo; reverted by `1ac8ac3`. Do not re-suggest unless asked.

## Pre-talk checklist (week of 2026-06-08)

- [ ] Warm the live app URL on 2026-06-10 morning AND 2026-06-11 morning
  (Streamlit Cloud cold-starts after ~7 days idle).
- [ ] Warm the techintel-quantum app the same way:
  https://dooling-techintel-quantum.streamlit.app/.
- [ ] Re-export `slides/sandia_talk_cmapss.pdf` if anything was changed
  since last compile.
- [ ] Bring `slides/app_walkthrough.pptx` on a USB or share via Drive for
  any deep-dive Q&A. Put the talk PDF **and** `slides/sandia_talk_cmapss.pptx`
  (image backup) on the same USB.
- [ ] Present the PDF in any viewer's full-screen/presentation mode (one
  Beamer page = one slide): Acrobat **Ctrl+L**, Evince **F5**, Okular
  **Ctrl+Shift+P**. For presenter view (next slide + timer + notes), use
  `pdfpc` — but notes are still `%` comments, so convert them to `\note{}`
  first if presenter notes are wanted.
- [ ] **Flip remaining "GPT-4o-mini" → "gpt-5.4-mini"** on slides 17, 19, 23,
  32 (slide 22 already done). The live app now runs gpt-5.4-mini.
- [ ] **Regenerate the PPTX image backup** (`build_talk_pptx.py`) — stale at 30
  slides; deck is now 33.
- [ ] **Trim to fit 45 min.** 33 frames ≈ ~1.3 min/slide is too tight; cut
  or merge before rehearsing. **OSINT stays and the unsupervised coda stays**
  (both kept per David 2026-05-28), so trim elsewhere — the quantum screenshots
  q01–q05 are the obvious candidates to thin.
- [ ] Screenshot the 2017 Springer paper landing page (DOI 10.1007/s10894-017-0123-4)
  → `slides/figures/openalex_screenshots/osint_roshan_paper.png` (the "payoff"
  slide has a placeholder box until then). Switched from the IPM seminar page
  2026-05-26 — that URL is geoblocked and unarchived; the paper is permanent.
- [ ] **Security-officer review** of the OSINT case-study module before
  presenting (slides make NO operational claims by design, but any framing
  of prior OSINT work as having produced outcomes needs separate clearance).

## Key design decisions (don't unwind without thinking)

- **Engine-grouped 60/20/20 split (seed=42).** Required to avoid leakage
  in run-to-failure data. Reviewer pushback on this gets the canonical
  answer in slide 5 (performance table) and the Run metadata tab of the
  app.
- **Two failure windows W ∈ {20, 50}.** Two LightGBM classifiers per
  subset: late-warning vs early-warning.
- **`is_unbalance=True`** in LightGBM to handle the rare-class skew
  (positive rate ~8% at W=20, ~25% at W=50).
- **Native LightGBM SHAP only.** `Booster.predict(X, pred_contrib=True)`.
  No `import shap`. Reason: keep tooling inside LightGBM, deterministic
  serialization, no version skew. See feedback memory
  `feedback_lightgbm_native_shap.md`.
- **Detection-half deck order (2026-05-25 restructure):** dataset →
  RUL-label/lifetime-invariance → regression-vs-classification (tree-line
  analogy) → pipeline → Optuna keyframes → "why 30 trials" (order-statistics
  floor) → metric definitions (precision/recall/FPR, ROC-AUC vs AUC-PR; why
  Optuna maximized AUC-PR to fight false positives) → performance → HiPlot
  per-cycle → take-away → **multi-window causal-chain bridge** (nested
  horizons; cardiac-arrest analogy; genericized DoD post-mission anecdote
  — satellite name omitted for releasability, the "external signal" = the
  Moon kept as a verbal reveal). The **global-SHAP and
  differential-SHAP slides were removed** (commented out via `\iffalse` in
  `cmapss/cmapss_block.tex`; figures + `build_phase3.py` intact, so fully
  restorable). The differential argument was previously the centerpiece — it
  and the **hypersonics** discovery slide (also commented out) can be brought
  back if desired.
- **Techintel-half OSINT case-study module (added 2026-05-26).** 5 condensed
  frames in `sandia_talk_cmapss.tex` after the quantum q01–q05 screenshots:
  hook → starting point (four signals in one byline) → following the people
  (3-career trajectory) → the payoff (2017 Springer paper by Roshan et al.,
  placeholder screenshot box) → methodology (6 steps). (The AI-acceleration/takeaway frame was removed
  2026-05-26 per DCD; module now ends on methodology.) Demonstrates open-source
  technical-literature analysis (NTU plasma-focus → Iran/IPM tech-transfer
  pattern). **ALL OPEN SOURCE; NO operational claims by design — the "what
  resulted" is deliberately UNSTATED** (DCD: that needs separate clearance).
  Names retained per the "people and places" intent (initializable if the
  security officer prefers). Speaker notes live as `%` comments above each
  frame. The "external, non-obvious signal" on the payoff slide = the Moon,
  kept off the slide and revealed verbally.
