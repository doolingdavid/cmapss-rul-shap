# Sandia talk — current state and resume recipe

Last updated: 2026-06-08 (see "## 2026-06-08 session" below: **demo reliability
hardened** — both HF Spaces upgraded to `cpu-upgrade` always-on; Streamlit Cloud
kept awake as a redundancy hedge via a GitHub Actions + Playwright keep-alive.
⚠️ Both have post-talk teardown steps — see that section.) Prior 2026-06-06 (**both demo
screencasts recorded, uploaded to YouTube unlisted, and linked in both the PDF
and PPTX** — link-only since the deck is emailed; deck still 34 frames, PPTX now
19 hotspots.) Prior 2026-06-04 (see "## 2026-06-04 session" below: **TWO new slides
added**, deck **32 → 34 frames**, notes re-keyed twice (PDF-page-based keys),
now **22 notes**. (1) PDF 12 "Reading the sensor names — a turbofan, front to
back": decoder for the engine-station sensor naming (Ps30, T30, Nc, …) right
before the live-app demo; (2) "Six flight conditions, one engine"
(KMeans regime-normalization for FD002/FD004) — **but then MOVED to a BACKUP
slide after Thank-you (now the last page, PDF 34) to keep the talk tight.** So
the **presented flow ends at Thank-you (PDF 33)**; the regime slide is page 34,
shown only on demand (jump to last page). ⚠️ Notes are keyed by PDF page, so
every insert/move forced a full downstream re-key — final alignment table is in
the session section.)
Prior 2026-06-03 (see "## 2026-06-03 session" below: **PRESENTER NOTES
slides 1–25 done**, dictation-and-polish flow; several lab/mission names pulled
OUT of the file per releasability, replaced with `[SAY ... ALOUD]` cues). Deck
was **32 frames** at end of 2026-06-03. Prior 2026-06-02 (see "## 2026-06-02 session" below:
**JNWC IQR backup
section REMOVED** — David cut it entirely to stay clear of any releasability
question. Deck now **32 frames**.) Prior 2026-06-01 (see "## 2026-06-01 session"
below): portfolio slide removed, close retitled, Thank-you github links removed,
+4-frame JNWC IQR backup section (since removed). Deck was 36 frames. Prior 2026-05-31 work in
"## 2026-05-31 session 2": gpt-5.4-mini flip finished, live-app link boxes,
title-slide update, Roxann email draft. Earlier 2026-05-31 work: 3 new slides → deck now **33
frames**, gpt-5.4-mini app migration shipped live, quantum screenshots
re-captured. CMAPSS pivot landed 2026-05-24; HiPlot parallel-coordinates view
added + deployed 2026-05-25; deck restructured (basics + Optuna slides added;
global/differential-SHAP and hypersonics slides removed; techintel screenshots
cropped). Latest app commit: `07569cb`. Deck now **30 frames** (2026-05-26:
metric-definitions slide added before the performance table; multi-window
causal-chain bridge slide added at the end of the CMAPSS half; **5-frame OSINT
case-study module** added to the techintel half after the quantum screenshots —
see note below. 2026-05-28: **2-frame unsupervised coda** added at the end of
the CMAPSS half — see "Unsupervised damage-evolution coda" below. It is
**additive**: David decided 2026-05-28 to **keep the OSINT module** (do NOT drop
it), so the deck carries both).
At **33 frames** the deck runs ~65 min at 2 min/slide; **needs a trim pass** to
fit the 45-min slot — trim elsewhere (quantum q01–q05), the OSINT module stays.
*(Update 2026-06-01: David is now MORE worried the talk runs SHORT — added a
skippable backup section as buffer. See "## 2026-06-01 session" below.)*

## 2026-06-08 session — demo reliability hardened (HF always-on + Streamlit hedge)

Goal: guarantee both live demos are ready at the **2026-06-11** interview with no
cold-start gamble. Two independent always-available hosts + the YouTube floor.

- **HF Spaces upgraded to paid always-on.** Both mirrors moved from `cpu-basic`
  (sleeps after ~48h) to **`cpu-upgrade`** ($0.03/hr, 8 vCPU/32 GB) — paid Spaces
  **never sleep by default**, killing the wake-up risk *and* the "SessionInfo"
  stale-tab popup (that was a sleep artifact). Verified both:
  `python hf_deploy.py status {cmapss|quantum}` → `stage=RUNNING hardware=cpu-upgrade`.
  This **reverses** the earlier 2026-06-06 "not worth paying for never-sleep" call —
  reframed from cosmetics to *guaranteed readiness*, which at ~$0.72/day each is cheap.
  ⚠️ **AFTER THE TALK: downgrade both to CPU Basic or Pause** (Settings → Space
  hardware) to stop the meter — else ~$43/mo for the pair. Paused/basic = free.
- **Streamlit Cloud kept as a redundancy hedge** (in case HF has a bad day during
  the talk — *not* as primary). Community Cloud has **no paid always-on tier**, so
  it's kept awake with a **GitHub Actions cron + Playwright** keep-alive in the
  `cmapss-rul-shap` repo: `.github/workflows/keepalive.yml` + `keepalive.js`,
  every 6h (sleep threshold ~12h) + manual `workflow_dispatch`. A bare HTTP ping
  does NOT keep Streamlit awake (it tracks the websocket session), so the job
  renders both apps in headless chromium and clicks the wake button if asleep.
  Pushed to `main` (`27f9855`); first manual run **27175918101 = green**, both
  apps rendered (`CMAPSS RUL … · Streamlit` + quantum, no errors).
  ⚠️ **AFTER THE TALK: disable the workflow** (Actions tab → keep-streamlit-awake
  → ⋯ → Disable workflow) so it stops running indefinitely.
- The deck's per-demo "Switch to live app" boxes already print **all three** links
  (Streamlit primary / HF mirror / YouTube ▶) — unchanged this session. If
  Streamlit is ever down on the day, click the HF mirror line; it's on every slide.
- **Streamlit Plotly bundle fix (later 2026-06-08).** After waking, the turbofan
  Streamlit app threw `Failed to fetch dynamically imported module:
  .../static/js/PlotlyChart.<hash>.js` when clicking a trace point — the lazy
  Plotly chunk hash drifted out of sync with the loaded page shell across a
  sleep→wake rebuild. Fix: **pinned `streamlit==1.57.0` and `plotly==6.7.0`** (was
  `streamlit>=1.36,<1.58` / `plotly>=5.22`) in `requirements.txt` + `pyproject.toml`
  (+ `uv lock`), so every rebuild produces identical chunk hashes. Pushed
  `249ce1c` → auto-triggered a clean Streamlit Cloud redeploy. Keep-alive holding
  it awake also stops the sleep→wake rebuild cycle that caused the drift. HF mirror
  is the always-on failsafe for the same click→SHAP-waterfall interaction.
- **Keep-alive hardened** (`e7edbb7`): the headless visitor now waits 8s for the
  sleep UI to render before checking for the "get this app back up" button and
  waits for it to disappear — the first version checked too early and left the
  quantum app asleep. Verified: run 27176244043 detected quantum asleep and woke it.

## 2026-06-06 session (later) — slide-6 indicator-symbol fix

Reviewer caught a broken glyph on **PDF page 6** ("Pipeline | supervised RUL
classification + native SHAP"), bullet 3 ("RUL + binary targets"). Root cause:
`\mathbb{1}[...]` — `amssymb` blackboard-bold only defines glyphs for letters
A–Z, so the double-struck digit **1** rendered as a missing/garbage glyph.
Fix: switched to **Iverson-bracket** notation `[\![ ... ]\!]` (renders ⟦…⟧),
which uses only base glyphs (no new package needed). Text updated "indicator
**function**" → "indicator **(Iverson) bracket**". Edit is in
`slides/cmapss/cmapss_block.tex` (gitignored — local only). Rebuilt **PDF**
(34 pages) and **PPTX** (34 slides, 19 hotspots, 22 notes) + pdfpc sidecar;
verified the rendered page visually. Both artifacts re-synced and email-ready.

## 2026-06-06 session — demo screencasts RECORDED, uploaded (unlisted), linked

Both live-app walkthrough screencasts are now **recorded, uploaded to YouTube as
Unlisted, and linked in the deck** — closing the long-open "YouTube screencasts
(not yet recorded)" item. **Decision: link-only, NOT embedded** — David is
emailing the deck, so a hyperlink keeps the file light (PDF stays 4.3 MB) and
avoids the PowerPoint media-embed fragility entirely.

- **CMAPSS turbofan** (per-cycle demo slide): `https://youtu.be/avTK6OyT92k`
- **TechIntel quantum** (per-article demo slide): `https://youtu.be/GBRZJSUuSJM`
- Wired via two new preamble macros in `slides/sandia_talk_cmapss.tex`:
  `\ytcmapssurl` / `\ytquantumurl`; each renders a red ▶ + accent-blue
  "recorded walkthrough on YouTube" `\href` line inside the existing "Switch to
  live app" box (`cmapss/cmapss_block.tex` for CMAPSS; inline quantum box ~L289).
- **Both formats rebuilt & in sync:** PDF (34 pp) + `build_talk_pptx.py` →
  `sandia_talk_cmapss.pptx` now **19 clickable hotspots** (was 17; the two new
  links auto-picked-up by `get_links()`), 22 presenter notes, `.pdfpc` refreshed.

**Recording/upload gotchas hit this session (for next time):**
- Streamlit "Record a screencast" gave **audio-only** (browser screen-capture
  selection/permission failed). Fallback that worked: just re-record; on Windows
  the robust path is **Win+Alt+R Game Bar** (records MP4 directly, no browser
  screen-share picker). David got valid WebMs in the end.
- CMAPSS raw WebM was 4:52; **trimmed last 16 s** via lossless ffmpeg
  stream-copy (`-t 276.36 -c copy`) → `slides/streamlit-streamlit_app-2026-06-06-07-39-31_trim.webm`
  (4:36), original kept. That trimmed WebM is what went to YouTube (YouTube
  accepts VP8/Opus directly — **no MP4 conversion needed for link-only**).
- Quantum WebM (`streamlit-quantum2d-2026-06-06-08-06-52.webm`, 8:13, 111 MB)
  uploaded as-is, no trim.
- ⚠️ **Do NOT use the `/embed/` URL for a clickable link** — the embed player is
  iframe-only and throws **"Error 153 / Video player configuration error"** when
  opened as a top-level link, even with embedding allowed. Use the plain
  `youtu.be/<id>` watch link. The recommended-video sidebar on the watch page is
  unavoidable via URL; mitigations = non-monetized channel shows no ads + hit
  **`f`** for fullscreen to drop the clutter when presenting.

**HF Spaces hardened against the "SessionInfo" popup.** The quantum HF mirror
threw a **"Bad Message Format — Tried to use SessionInfo before it was
initialized"** popup. Root cause: **stale browser tab/cache reconnecting after
the free-tier Space slept** (Incognito loaded clean → confirmed it's a transport
/ stale-tab issue, NOT a server crash; `stage=RUNNING` throughout). It is
**cosmetic and self-healing — a refresh / fresh tab fixes it 100%**. Belt-and-
suspenders fix applied to **both** HF Dockerfiles in `~/jobs/hf_deploy.py`: launch
Streamlit with `--server.enableCORS=false --server.enableXsrfProtection=false`
(hardens the websocket handshake through HF's reverse proxy). Both redeployed +
verified `RUNNING` / `/_stcore/health` = `ok` / HTTP 200. Persisted in the deploy
script, so future redeploys keep it.
- **Talk-day habit (more important than any paid tier):** warm both Spaces ~30 min
  before (open the URLs), **open a FRESH tab right before demoing**, and
  Ctrl+Shift+R if the popup ever flashes. Paying for HF "never sleep" removes the
  main trigger but is **not** an absolute guarantee — decided NOT worth it given
  the refresh-fixes-it reality + triple redundancy (Streamlit Cloud → HF mirror →
  YouTube recording).

## 2026-06-04 session 2 — Hugging Face Spaces live backups DEPLOYED

Risk-reduction layer: both live Streamlit demos now have an **independent second
host** on HF Spaces (Streamlit Community Cloud kept as primary). Broader plan also
includes ~90s YouTube screencasts (not yet recorded) + the proven local-MP4 embed
as the offline floor — see the demo-video NEXT STEP section below.

- **CMAPSS** → https://huggingface.co/spaces/dcdooling/cmapss-rul-shap
  (app host: https://dcdooling-cmapss-rul-shap.hf.space) — no secrets.
- **Quantum** → https://huggingface.co/spaces/dcdooling/techintel-quantum
  (app host: https://dcdooling-techintel-quantum.hf.space) — secrets
  `OPENAI_API_KEY` + `MAPBOX_TOKEN` set in Space settings (copied from the real
  local `.streamlit/secrets.toml`; the line-1 "dummy" comment is STALE — key IS real).
- **HF retired the built-in `streamlit` SDK** → both Spaces use the **Docker SDK**.
  Deploy is scripted: `~/jobs/hf_deploy.py {cmapss|quantum|status <name>}`. It
  uploads exactly the git-tracked file set of each source repo (parity with
  Streamlit Cloud) + a generated `Dockerfile` + HF `README.md` frontmatter
  (`sdk: docker`, `app_port: 7860`). Big quantum files (.html 24MB, two .pkl.gz)
  auto-handled as LFS. Quantum's Dockerfile CMD writes `.streamlit/secrets.toml`
  from injected env-var secrets at startup (app code unchanged).
  **CMAPSS Dockerfile must `apt-get install libgomp1`** — LightGBM needs the
  OpenMP runtime, absent from `python:3.12-slim` (first build crashed without it:
  `OSError: libgomp.so.1: cannot open shared object file`).
  HF account = `dcdooling`. Source repos: `doolingdavid/cmapss-rul-shap`,
  `doolingdavid/techintel-quantum-talk`.
- HF Spaces free tier (cpu-basic) **sleeps after ~48h idle** → warm both ~30 min
  before the talk (just open the URLs).
- ⚠️ The HF write token used to deploy was pasted in chat → **revoke it** at
  https://huggingface.co/settings/tokens and mint a fresh one if needed.

### ✅ DONE — HF URLs wired into the deck (+ QR codes)
HF "backup mirror (Hugging Face)" lines added next to every Streamlit URL via a
preamble macro `\hfmirrorline{url}{display}` + `\hfcmapssurl`/`\hfquantumurl`
(muted gray, `\definecolor{mirror}`). Locations: title slide, CMAPSS per-cycle
"Switch to live app" box (cmapss_block.tex), quantum pipeline box, quantum
per-article box, portfolio/close slide, Thank-you slide. All HF links are
`\href` → `build_talk_pptx.py` `get_links()` picks them up automatically (no
`PLAIN_URLS` change needed); PPTX now has **17 clickable hotspots** (was 10).
**QR codes** (generated by `uv run --with "qrcode[pil]"`, in `slides/figures/`):
- Thank-you slide: **four** codes, two per app — Streamlit primary (accent-blue,
  `qr_cmapss.png`/`qr_quantum.png`) + HF mirror (gray, `qr_hf_cmapss.png`/
  `qr_hf_quantum.png`), labeled "Streamlit" / "HF mirror" with URLs beneath.
- Both demo slides (CMAPSS per-cycle, quantum per-article): a small **HF-backup**
  QR ("scan = HF backup") sits to the right of the "Switch to live app" box, so a
  failed live app can be recovered by scanning straight to the HF mirror. The
  box was restructured into two minipages (text 0.66 + QR 0.16).
Deck still **34 pages**, clean compile, no overfull boxes.

### ⏭️ STILL TODO on the redundancy layer
1. **YouTube screencasts** (~90s each) + keep the local MP4 embed as offline floor.
2. Confirm the Sandia venue network allows HF/YouTube.

## 2026-06-04 session

**TWO new explainer slides added this session** (deck 32 → 34 frames; PPTX → 34
slides; notes re-keyed twice, now 22). Both were prompted by David asking what
things meant; the answers worked well enough that he asked for audience slides.
**Final verified alignment** (note key → PDF page) at session end:

| PDF | slide | note? |
|---|---|---|
| 11 | Performance (8 models) | 11 |
| **12** | **Reading the sensor names — a turbofan, front to back** (NEW) | **12** |
| 13 | Per-cycle explainability (live app) | 13 |
| 14 | Take-away | — (blank) |
| 15 | Why several windows | 15 |
| 16 | Now drop the labels | 16 |
| 17 | The data draws its own degradation map (heatmap) | 17 |
| 18 | The signal behind the map | 18 |
| 19 | Same thesis, different data | 19 |
| 20 | Pipeline (LLM/OpenAlex) | 20 |
| 21 | The magic | 21 |
| 22–25 | quantum scatter / drilldown / country / 3-D | — |
| 26 | per-article LLM assessment | 26 |
| 27–31 | OSINT | — |
| 32 | The hard part isn't capability — it's trust | — |
| 33 | **Thank you (end of presented flow)** | — |
| **34** | **Backup — "Six flight conditions, one engine" (regime-norm)** | **34** |

**The regime slide is now a BACKUP at PDF 34**, after Thank-you (moved there
2026-06-04 to keep the 45-min talk tight). The presented flow ends at Thank-you
(PDF 33). **To show the backup live:** it's the last page — in a PDF viewer
(pdfpc/Acrobat/Okular) type `34` + Enter; in PowerPoint type `34` + Enter during
the slideshow. The frame lives at the end of `sandia_talk_cmapss.tex` (search
"BACKUP SLIDE"); note 16 ("Now drop the labels") still mentions the wrinkle
verbally and points to the backup.

A programmatic check (render each PDF page's title next to its note's first
sentence) confirmed every key lands on the right slide. **Re-run that check
after any future frame insert/remove** — keys are PDF-page-based, NOT
auto-aligned.

### Slide A — "Reading the sensor names" (PDF 12)

Inserted in `cmapss/cmapss_block.tex` right after the Performance table and
before the per-cycle app demo, so the audience can decode names like `Ps30`,
`T30`, `Nc`, `Nf`, `T50` the moment they appear in the SHAP waterfall. Layout: a
front-to-back gas-path strip (intake → Fan → LPC → HPC → combustor → HPT → LPT →
nozzle, colored \colorbox modules) → a legend (**letter** = quantity: T temp / P
total press. / Ps static press. / N shaft speed / W coolant flow; **number** =
gas-path station: 24 LPC-exit / 30 HPC-exit / 50 LPT-exit) → two decoder tables
→ a cloud callout reading `Ps30` aloud and tying it to the HPC fault. Reinforces
the "named features, not a black box" thesis. Note 12 added (David's voice).
**HPC = High-Pressure Compressor** — the fault mode in FD001/FD003; that's why
Ps30/T30/P30 dominate. The "30" = engine station 3 (HPC exit / combustor inlet).

### Slide B — regime-normalization (now PDF 17)

**New audience-facing explainer slide + presenter-note renumber.** David didn't
follow what the "6-condition subsets" bullet on the unsupervised slide (PDF 15,
"Now drop the labels") actually meant. After a detailed walk-through (the three
operating channels are *commanded* dials, not a regime label; KMeans recovers
the six buckets; clustering runs over the WHOLE life because settings don't
degrade, but the healthy baseline is taken from the first quarter, separately
within each regime), he asked for a dedicated slide.

- **NEW frame, "Six flight conditions, one engine — recover the
  regime, then z-score *within* it"** (in `cmapss/cmapss_block.tex`, inserted
  between "Now drop the labels" and the heatmap "The data draws its own
  degradation map"; landed at PDF 16, then Slide A bumped it to **PDF 17**).
  Layout: framing paragraph → the three commanded channels
  named explicitly (**altitude · Mach number · throttle-resolver angle (TRA)**)
  → two columns: left = table of the six KMeans-recovered regimes (sea-level/
  M0.00 … 42k ft/M0.84, TRA 60 or 100); right = 3-step logic (cluster over whole
  life / baseline from first quarter within regime / score each cycle vs its own
  regime baseline) → cloud punchline box (1 baseline for FD001/FD003, 6 for
  FD002/FD004). Builds clean, no overflow.
- **Deck reached 33 frames with this slide, then 34 after Slide A.** PPTX image
  backup regenerated to **34 slides** (still 10 clickable hotspots).
- **Also tightened the "6-condition" parenthetical** on the "Now drop the
  labels" slide (final PDF 16) — names FD002/FD004, says *why* (a sensor swings
  on operating point alone).
- **⚠️ PRESENTER NOTES RE-KEYED TWICE.** `presenter_notes.py` keys are PDF page
  numbers, so each insert shifted every later note. Slide B's insert: 16→17,
  17→18, 18→19, 19→20, 20→21, 25→26 (and the regime deep-dive was MOVED out of
  note 15 into a NEW note 16). Slide A's insert then shifted everything from
  old-12 onward by +1 again (12→13, 14→15, 15→16, 16→17, … 26→27) and added a
  NEW note 12. **Final alignment is the table at the top of this session** —
  trust that, not the intermediate remaps. Total now **22 notes**. *(Any future
  frame insert/remove → re-key by hand, descending, then re-run the alignment
  check.)*
- Q&A prep captured for "why k=6?": elbow + silhouette both pick 6 unaided
  (within-cluster spread → ~0 at k=6, silhouette peaks 0.997 then falls); erring
  high is safe (splits a real regime), erring low merges two and re-contaminates;
  HDBSCAN (the techintel half's clusterer) is the no-k callback.

### Other note edits this session (no slide changes, PPTX rebuilt)

- **Slide 12 sensor names VERIFIED against the primary source.** Cross-checked
  every name on the new decoder slide against **Table 2 of the Saxena-Goebel
  paper** (`data/cmapss/Damage Propagation Modeling.pdf`) and the dataset
  `readme.txt`. All 15 correct incl. the four key ones (Ps30=static@HPC-exit,
  phi=fuelflow÷Ps30, W31=HPT-coolant, W32=LPT-coolant). The repo's
  `src/cmapss/load.py` `_RENAME` dict is where the physical names live (it
  attributes them "per Saxena/Goebel"); raw `.txt` files have no headers. Caveat
  for Q&A: paper's sim envelope says "up to 40,000 ft" but FD002/4 data's top
  regime is 42,000 ft (canonical CMAPSS conditions); slide follows the data.
- **Slide 10 note expanded** with two Q&A-driven paragraphs: (1) **AP vs
  F-score** — F1 grades one threshold (~0.5), average precision grades the whole
  PR curve; optimizing F1 secretly tunes to a deploy-threshold we'd never use,
  so AP keeps model-selection threshold-free. (2) **How AP is computed in the
  objective** — per `src/cmapss/train.py:_objective`: GroupKFold(5) by engine →
  `average_precision_score` on each held-out fold → `np.mean` of the folds is
  the per-trial value Optuna maximizes → best params refit on full train.
  (Degenerate zero-positive folds skipped; LightGBM's internal
  `metric=average_precision` is cosmetic — no early stopping.)

### ⏭️ NEXT STEP (deferred — David will record videos later)

**Demo-failure fallback videos — PIPELINE VALIDATED 2026-06-04.** David wants
screen-recordings of the two live Streamlit demos embedded in PowerPoint to
"break glass" if a live app cold-starts / errors / the wifi dies. **End-to-end
test passed:** a 2:36 Streamlit screencast (WebM) → converted to MP4 → embedded
via python-pptx `add_movie` → **both the standalone MP4 AND the embedded .pptx
played in David's PowerPoint** (so his PowerPoint/license is fine; the earlier
"cannot play media" was a corrupt MP4, not a license issue).

**THE WORKING RECIPE (use this for the real recordings):**
- **Record** with Streamlit's "Record a screencast" (saves WebM, ~1920×1040, no
  audio) OR Xbox Game Bar / PPT Insert→Screen Recording (MP4 directly).
- **Convert WebM→MP4** with the bundled ffmpeg (no system install needed —
  `uv run --with imageio-ffmpeg python ...; imageio_ffmpeg.get_ffmpeg_exe()`):
  ```
  ffmpeg -y -fflags +genpts -i in.webm -r 24 -c:v libx264 -preset veryfast \
         -crf 25 -pix_fmt yuv420p -an -movflags +faststart out.mp4
  ```
  → ~19 MB for 2.5 min, H.264 High/yuv420p/24fps, moov present. Verify with
  `ffmpeg -i out.mp4` (must NOT say "moov atom not found").
- **⚠️ Three gotchas we hit, all now solved by the recipe above:**
  1. Chrome/Streamlit WebM carries a **bogus "1000 fps" (1k tbr) timebase** —
     without an explicit `-r 24` libx264 balloons the file to 100 MB+ and never
     effectively finishes. The `-r 24` is mandatory.
  2. **Don't convert in the background and embed before it finishes** — that race
     produced a moov-less corrupt MP4 → PPT "cannot play media." Convert
     foreground / wait for rc 0, THEN embed.
  3. Streamlit screencast has **no audio** → use `-an`. `+faststart` needed for
     PPT. WebM itself is fine as a recording but PowerPoint cannot play WebM.
- **Poster frame** (so the slide shows the app, not a generic icon):
  `ffmpeg -ss 00:01:15 -i out.mp4 -frames:v 1 -update 1 poster.png`, pass to
  `add_movie(poster_frame_image=poster)`.

**Embedding rule:** the auto-built `sandia_talk_cmapss.pptx` is regenerated from
the PDF on every `build_talk_pptx.py` run, so hand-embedded videos there get
WIPED. Plan (David leaned this way, now confirmed viable):
- Wire `add_movie` into `build_talk_pptx.py`, keyed by slide number, so dropping
  `demo_cmapss.mp4` / `demo_quantum.mp4` into a known folder auto-embeds them
  full-screen on the **presented-flow demo slides (13 = per-cycle app, 26 =
  per-article)** and they survive rebuilds. Guard behind "if .mp4 exists."
  Set Playback → Start On Click + Play Full Screen + Rewind via the XML if
  feasible (default add_movie is click-to-play, which is acceptable).
- **ALSO keep the standalone MP4s as the can't-fail backup:** double-click to
  play full-screen in the Windows media player (no PowerPoint/license needed).

**Proof artifacts in `slides/` (test only — David will record the real two):**
`streamlit-streamlit_app-2026-06-04-18-07-06.webm` (source test), VALID
`demo_turbofan.mp4` (18.9 MB), `demo_turbofan_poster.png`, `demo_video_test.pptx`
(19 MB, plays). These are the turbofan-app TEST; the real ones go to
`demo_cmapss.mp4` (slide 13) and `demo_quantum.mp4` (slide 26).

**To resume this:** "wire the demo fallback videos into build_talk_pptx.py" —
the real MP4s (or WebMs to convert with the recipe above) will be in hand.

### pdfpc presenter-view sidecar (NEW build artifact)

David asked to wire up a PDF presenter view (next slide + timer + notes), not
just the PPTX notes pane. Added **`slides/build_pdfpc.py`**: regenerates
`slides/sandia_talk_cmapss.pdfpc` from the SAME `presenter_notes.py` `NOTES`
dict (INI-like pdfpc format: `[file]`/`URI=` + `[notes]` with `### <page>`
markers; deck has no overlays so page == user-slide == note key). Wired a
non-fatal call into `build_talk_pptx.py`, so **one `build_talk_pptx.py` run now
refreshes BOTH the .pptx and the .pdfpc** (single-sourced, never drift). pdfpc
itself is **not installed** here (`sudo apt install pdfpc` / `brew install
pdfpc`); it's a GTK dual-window GUI so on WSL2 it needs WSLg/X — run on the
presentation laptop. Launch: `pdfpc slides/sandia_talk_cmapss.pdfpc`.

## 2026-06-03 session

**Presenter notes — slides 1–25 drafted** (was 1–5 at start of session). Same
mechanism as before: notes live in **`slides/presenter_notes.py`** (`NOTES`
dict keyed by **PDF slide number**), injected into the PPTX notes pane by
`build_talk_pptx.py` on every rebuild. David dictates a slide's notes, Claude
lightly polishes (his voice/terms), adds to the dict, rebuilds.

- **DONE: slides 1–12, 14, 15, 16, 17, 18, 19, 20, 25** → **20 presenter notes**.
- **Slide 13** (CMAPSS take-away) **intentionally left blank** — self-explanatory.
- **Slides 21–24** (quantum screenshots: landing scatter / drilldown /
  country-country / 3-D affiliation map) **skipped for now** — David may add
  later. Slide 25 (per-article LLM assessment) is the live-demo click-path.
- **NEXT: slides 26–32** (OSINT case study, hypersonics, the trust close) —
  David to decide whether they need notes. Slide 25 may still get more if he
  plays with the app more.

**⚠️ RELEASABILITY — names kept OUT of the file.** Per David's call, identifiers
are NOT written in `presenter_notes.py`; instead the notes carry neutral
`[SAY NAME ALOUD]` / `[SAY WHERE ALOUD]` cues so David decides verbally, live,
based on who's in the room (cleared + need-to-know is his + his security
officer's determination, not ours). Specifically genericized:
- **Slide 14** satellite mission name → `[SAY NAME ALOUD]` (the lunar-phase /
  attitude-saturation post-mortem story; RSC-Kirtland confirmation kept).
- **Slide 16** customer affiliation (was "LANL") → `[SAY WHERE ALOUD]` (the
  "is this machine degrading?" ruptures regime-shift anecdote).
- **Slide 20** "people from LLNL call UMAP magic" — LEFT AS IS (casual opinion,
  not a finding; David explicitly OK'd keeping it).
Grep check `LANL\|STP-Sat` in presenter_notes.py returns 0.

**DEMO CLICK-PATHS verified against artifacts this session (so they render live):**
- **Slide 12** (CMAPSS app): FD003, window 50, **validate** split, **engine 54,
  cycle 163** — confirmed exists; pred 0.919, y_true=1, SHAP waterfall 97.5%
  RED, top driver **Ps30** (HPC outlet static pressure) — physically perfect for
  FD003=HPC fault. Bonus: engine 54's only misfires are cycles 142–143 (true-0,
  predicted ~0.79–0.88), i.e. 1–2 cycles shy of the true 0→1 transition at
  cycle 144 — concrete proof of the "misfires hug the transition" claim.
- **Slide 15**: FD003 heatmap engine is **#14** (NOT the demo's #54); its Ps30
  z-score climbs to ~10 (max|z|≈11.5) at end of life — same sensor the demo's
  SHAP flagged, so supervised + unsupervised independently finger the same
  physics. (Heatmap engines: FD001 #9, FD002 #111, FD003 #14, FD004 #137.)
- **Slide 25** (techintel-quantum app, data at
  `~/jobs/openalex_local/techintel-quantum/updatejammingdfinfo2d.pkl.gz`,
  24,359 rows): **CORRECTED a coordinate** — the China post-quantum article
  ("A High Throughput and Configurable Pseudo-random Number Extension
  Generator...", Huazhong Univ, Wuhan; lattice-based) is in **topic 38** but at
  **x≈−1.98, y≈1.14** (the cluster's x-MIN, far-WEST edge), NOT David's
  remembered x=0.99/y=1.03. Note now says "far-left/west edge." Toshiba/A.J.
  Shields (UK) ✓ present incl. topic 38. **Quantropi (Ottawa, Canada)** ✓ 14
  papers, some in topic 38 (rest are HDBSCAN noise, cluster −1) → the SOF-Week
  reveal holds. **Cluster 86** ✓ at x≈2.18, y≈−4.22 (David's ~2.1/−4.1), small
  (51 papers, tight blob). ⚠️ Axis-orientation caveat: x-values are from the
  dataframe; if the app reverses an axis the "west/left" cue flips — David to
  eyeball orientation in the app once.

**Build gotcha:** `build_talk_pptx.py` imports `fitz` (PyMuPDF), which is NOT in
`pyproject.toml`/`requirements.txt`. Build it with
`uv run --active --with pymupdf python slides/build_talk_pptx.py`. (Offered to
add pymupdf as a dep; not yet done.) Run from the **repo root**, not `slides/`.

**Open offer (declined/deferred):** an order-statistics "priest joke" tangent
for slide 8 (German tank problem / secretary 37% / Hubbard Rule-of-Five) was
drafted and David passed; stashable later if wanted. Also offered: adding
`pymupdf` to deps; moving the Mapbox token to `st.secrets` if it's hard-coded in
the quantum app repo (David uses a FREE Mapbox public token — fine for the demo,
no credit card needed; just URL-restrict the `pk.` token).

## 2026-06-02 session

**Removed the JNWC current-work backup section entirely.** David decided not to
tread anywhere near a security violation, so the 4-frame JNWC IQR
flight-verification backup (added 2026-06-01) is **out of the presentation**.
Wrapped in `\iffalse … \fi` in `slides/sandia_talk_cmapss.tex` (not hard-deleted
— recoverable for a cleared venue) so it does NOT compile. Deck **36 → 32
frames**, builds clean. **PPTX image backup regenerated to 32 slides** (still 9
clickable hotspots — the JNWC frames had no live-demo links). `figures/
jr_local_noise_demo.png` left in place, now unreferenced/harmless.

**Also this session — slide 6 indicator-function definition.** On the
"Pipeline | supervised RUL classification + native SHAP" frame (PDF slide 6,
`cmapss/cmapss_block.tex` bullet 3), defined the `$\mathbb{1}[\cdot]$` symbol
inline as the **indicator function** (1 if condition holds, else 0) with a
clickable `\href` to the Wikipedia "Indicator function" page. Deck rebuilt
clean; that link is now also a clickable hotspot in the PPTX (hotspot count
9 → 10).

**Also this session — PRESENTER NOTES infrastructure (IN PROGRESS).** David is
dictating speaker notes one slide at a time; I lightly polish them (his voice,
his content/terms — e.g. he uses "CAG = Context-Augmented Generation") and inject
them into the PPTX notes pane. Mechanism (so notes survive rebuilds):
- Notes live in **`slides/presenter_notes.py`** — a `NOTES` dict keyed by
  **PDF slide number** (1-based, matching `sandia_talk_cmapss.pdf` page order;
  remember PDF slides 3–17 come from `cmapss/cmapss_block.tex`).
- `build_talk_pptx.py` imports `NOTES` and injects each into
  `slide.notes_slide.notes_text_frame.text` on every build. Edit notes in the
  .py, re-run `python slides/build_talk_pptx.py`. Build line now reports
  "N presenter notes".
- **DONE so far: slides 1, 2, 3, 4, 5.** (1 title, 2 "One thesis", 3 CMAPSS
  dataset, 4 RUL lifetime-invariance, 5 regression-vs-classification.) Slide 3
  note says "the winning AFRL hyperspace challenge submission".
- **NEXT: slide 6** (the Pipeline frame) and onward — David will dictate; same
  polish-and-inject flow. ~26 slides still need notes (deck is 32 frames).

**Consequence for the open items:**
- **Security-officer review is now lighter** — only the OSINT case study
  remains to clear (no operational claims by design; the "what resulted" is
  deliberately unstated). The EW-content concern is gone with the JNWC cut.
- **Length: the SHORT-runs-short worry is now more live** — the JNWC section
  was the skippable buffer, and it's gone. At 32 frames, if a rehearsal comes
  in under 45 min, candidates to *restore*: bring back the JNWC genericized
  variant (only after security sign-off), the global/differential-SHAP slides
  (`\iffalse` in cmapss_block.tex, fully restorable), or the hypersonics
  discovery slide. Trimming is no longer the concern.

## 2026-06-01 session

Nitpick cleanup + a backup section + clickable-PPTX upgrade. Deck **33 → 36
frames** (net: −1 removed, +4 backup). Builds clean each time. **PPTX image
backup regenerated to 36 slides AND now has clickable hyperlinks** (see below);
`app_walkthrough.pptx` not re-run this session (native-text, unaffected by these
edits — regenerate if its content ever changes).

- **Removed the Portfolio slide** ("the pipeline is the artifact"). David does
  NOT want the audience navigating to his GitHub pages. Wrapped in `\iffalse`
  (restorable), not hard-deleted.
- **Retitled the close** "Why this fits Sandia" → **"The hard part isn't
  capability --- it's trust"** (less begging-to-be-hired; reframed around the
  adoption/trust thesis). Bold lead-in now ties explanation primitives to
  adoption. Dropped "load-bearing" (LLM tell) → "increasingly central to".
  **Removed the patent/SBIR bullet** (most résumé-ish, cut against the reframe).
- **Thank-you slide:** removed the three `github.com/...` repo links; keeps the
  two live-demo Streamlit URLs, email, LinkedIn.
- **PPTX image backup is now clickable.** `build_talk_pptx.py` rewritten: after
  laying each full-bleed page image it overlays transparent, hyperlinked
  rectangles over every demo URL — positioned automatically by harvesting the
  PDF's `\href` link annotations (pages 12/13/25) and text-searching the
  plain-text demo URLs (Thank-you + title + techintel slides), de-duped. 9
  hotspots total. Rectangles use a ~1%-opacity fill (invisible but
  full-area-clickable in PowerPoint). Regenerated `sandia_talk_cmapss.pptx` to
  36 slides. Slide image is still pixel-identical to the Beamer PDF.
- **NEW 4-frame BACKUP section** before Thank-you — current **JNWC IQR
  flight-verification filtering** (from `~/jobs/jr_filtering_deck.pptx`; IQR
  ONLY per David — SSA/NMF deliberately excluded). Frames: (1) divider/bridge
  "same move, a different signal"; (2) the J/R GO-NO-GO decision (30 dB floor,
  why a naive minimum false-FAILs); (3) two-pass Tukey 1.5×IQR fences → clean
  1st-pct floor, with figure `figures/jr_local_noise_demo.png` (copied from
  `~/jobs/`); (4) "Same philosophy, made defensible" — explicit tie-back to the
  techintel HDBSCAN noise-drop (30% dropped → tight clusters/invisible
  colleges), k-sweep defensibility. Speaker notes are `%` comments per frame.
  **⚠️ RELEASABILITY (open item):** this is current-program EW content (J/R,
  cover-jammer, 30 dB) — needs the SAME security-officer review as the OSINT
  module, arguably more. A **genericized variant** (drop J/R / cover-jammer /
  soften threshold) was offered; David to decide which version presents. Source
  pptx narrative had 25 slides incl. SSA/NMF lenses if more is ever wanted.

**NEXT SESSION (David's plan, 2026-06-01):** write **presenter notes into the
PowerPoint** — David has good spoken notes that are deliberately NOT on the
slides; he'll run them by Claude first. The Beamer `%` speaker-note comments are
a starting point but David's are richer/different. Mechanically, presenter notes
live in `slide.notes_slide.notes_text_frame.text` per slide via python-pptx.
**Heads-up:** re-running `build_talk_pptx.py` rebuilds the PPTX from scratch, so
notes must be injected by the build (add a notes pass / companion script), not
hand-typed into the file — otherwise the next regenerate wipes them.

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
*(↑ both RESOLVED in session 2 below.)*

## 2026-05-31 session 2

- **Model rename FINISHED**: all `GPT-4o-mini` → `gpt-5.4-mini`. 5 mentions in
  `slides/sandia_talk_cmapss.tex`, 6 in `slides/build_walkthrough_pptx.py`.
  Cost line de-priced ("fractions of a cent per writeup", dropped the
  $0.001 / 2025-pricing figure). Zero `4o-mini` left anywhere.
- **PPTX rebuilds DONE** (both via PyMuPDF/`fitz` — poppler is NOT installed and
  NOT needed; `build_talk_pptx.py` imports `fitz`):
  - `slides/sandia_talk_cmapss.pptx` — 33 slides @ 200 DPI (image backup of the PDF).
  - `slides/app_walkthrough.pptx` — native-text walkthrough; fixed a latent
    `slide`→`s` NameError in `build_walkthrough_pptx.py` so it builds.
- **Live-app link boxes added** (clickable `\href`, styled like the slide-5 box):
  - Slide 25 (per-article LLM assessment) → quantum app, with demo cue
    (topic 38 → article → Affiliations → US/CN OpenAlex page → real URL).
  - Turbofan PDF slide 14 (Per-cycle explainability) → upgraded the plain-text
    URL to the clickable cmapss-rul box.
  - Turbofan PDF slide 15 (Take-away) → added the clickable cmapss-rul box.
- **Title slide updated**:
  - author: "Principal Data Scientist" → "RF Data Analyst, CACI International
    Inc | supporting the Joint Navigation Warfare Center".
  - subtitle → "Auditable Prediction and Discovery, from Turbofan Prognostics
    to Open-Source Technology Intelligence". `\title` unchanged
    ("ML/AI as an Organizational Lens").
- **Email to Roxann (rrlapp@sandia.gov)**: standalone Gmail draft created
  (ID `r1539512532323228926`) with the agreed title + abstract + PDF/hyperlinks
  note. **NOT threaded** into her original email (Gmail thread-search blocked by
  auth scope). Next: send it (or paste body into a direct reply), then send the
  deck PDF 1–2 days before June 11.
- Deck builds clean at **33 pages** after every edit; PPTX refreshed each time.

**Demo plan (verbal, not on slides):** at the techintel half, skim slide 25,
then switch to the live quantum app → topic 38 → an article → Affiliations tab
sorted so companies list first → open US/CN firms' OpenAlex pages to reach their
real company URLs. The Iranian plasma-focus vignette STAYS in the slides but is
skipped during the live demo.

**Gotcha — slide numbering:** PDF slides 3–17 come from
`slides/cmapss/cmapss_block.tex` (`\input` at ~line 102 of the main file). So
main-file `\begin{frame}` numbers ≠ PDF slide numbers. Map: titlepage=1,
"One thesis"=2, cmapss_block frames=3–17, "Same thesis, different data"=18, …,
per-article LLM assessment=25.

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
| **Main 45-min deck** | `slides/sandia_talk_cmapss.tex` → `.pdf` | **34 pages, but presented flow is 33** (ends at Thank-you, PDF 33; PDF 34 is the regime-norm BACKUP shown only on demand). 2026-06-04: +sensor-name decoder at PDF 12, +regime-norm as backup at PDF 34; JNWC IQR backup removed 2026-06-02, `\iffalse`-wrapped + recoverable). `slides/` is gitignored — local only |
| **Deck figures** | `slides/cmapss/figures/`, `slides/figures/openalex_screenshots/` | Optuna: `build_optuna.py`; RUL+analogy: `build_basics.py`; HiPlot: `hiplot_view.png`; cropped techintel: `q0*_*.png`; global-SHAP (now unused): `build_phase3.py` |
| **Unsupervised coda** | `slides/cmapss/build_unsupervised.py` → `figures/unsupervised_heatmap.{png,html}` | Purely-unsupervised damage-evolution heatmap (see section below). PNG for the deck, HTML for interactive hover. Needs `vl-convert-python` (local venv only). |
| **Walkthrough deck** | `slides/app_walkthrough.pptx` | native-text PowerPoint, generated by `slides/build_walkthrough_pptx.py` (regenerated 2026-05-31 session 2) |
| **Notes handout (print)** | `slides/sandia_talk_notes_handout.html` | Self-contained HTML (base64 thumbnails) — the print/paper backup for a single-monitor laptop. Per slide: number + title + thumbnail + FULL notes (never clipped, unlike PPTX Notes Pages). Built by `slides/build_notes_handout.py` from `presenter_notes.py`. Copy to laptop → open in browser → Ctrl+P (or Save as PDF). |
| **pdfpc sidecar** | `slides/sandia_talk_cmapss.pdfpc` | Presenter-view notes for the PDF (next-slide + timer + notes via `pdfpc`). Auto-generated from `presenter_notes.py` by `slides/build_pdfpc.py` (also runs inside `build_talk_pptx.py`). Launch: `pdfpc slides/sandia_talk_cmapss.pdfpc`. pdfpc not installed locally; GTK GUI needs WSLg/X. |
| **PPTX backup of talk** | `slides/sandia_talk_cmapss.pptx` | 34 slides, one full-bleed image per slide (pixel copy of the Beamer PDF), **plus 9 clickable hyperlink hotspots** over the live-demo URLs. Non-editable venue fallback. Regenerate after any deck change: `slides/build_talk_pptx.py` (renders the PDF → 16:9 PPTX via PyMuPDF + python-pptx). |

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

# Rebuild the PPTX backups (~1-3 s each):
python slides/build_talk_pptx.py           # -> sandia_talk_cmapss.pptx (image backup, fitz) + .pdfpc sidecar
python slides/build_pdfpc.py               # -> sandia_talk_cmapss.pdfpc only (pdfpc presenter notes)
python slides/build_notes_handout.py       # -> sandia_talk_notes_handout.html (print/paper backup, full notes)
python slides/build_walkthrough_pptx.py    # -> app_walkthrough.pptx (native text)

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

- [ ] **⛳ GATING QUESTION — own laptop vs SNL machine?** David emailed Roxann
  (rrlapp@sandia.gov) 2026-06-04 asking whether he presents from his own laptop
  or a Sandia computer. **Awaiting reply.** This determines the whole
  materials-delivery plan. ⚠️ David **cannot bring a USB** into SNL, and SNL
  likely **blocks personal Google Drive / webmail** — so do NOT rely on
  downloading artifacts at the event.
  - **If OWN laptop (push for this):** everything is local — PDF, PPTX, embedded
    videos all on his machine, videos play OFFLINE so demos work with no Wi-Fi.
    Just confirm the projector connector (HDMI/USB-C/VGA — bring an adapter) and
    whether guest Wi-Fi allows `*.streamlit.app` (live demo is a bonus; videos
    are the real demo; in-deck screenshots are the floor).
  - **If SNL machine:** email the **PDF (4.4 MB)** to Roxann ahead of time so she
    pre-loads it (small, works). The **video PPTX (~50 MB) likely can't be
    delivered** (too big to email, Drive may be blocked) → demo fallback reverts
    to the static screenshots already in the deck + `app_walkthrough.pptx`.
  - Follow-ups to ask once she replies: guest Wi-Fi? projector input/adapter?
    USB policy (confirm the ban)?
- [ ] **Record demo-failure fallback videos** of both live apps and embed them
  as a "break glass" backup (MP4/H.264, embed-not-link, full-screen on click).
  See "⏭️ NEXT STEP" in the 2026-06-04 session for the plan + the decision to
  wire `add_movie` into `build_talk_pptx.py` (slides 13 & 26). Deferred — David
  will record later.
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
  **Ctrl+Shift+P**. **For presenter view (next slide + timer + notes): use
  `pdfpc slides/sandia_talk_cmapss.pdfpc`.** The `.pdfpc` sidecar is now
  auto-generated from `presenter_notes.py` by `build_pdfpc.py` (and on every
  `build_talk_pptx.py` run), so the speaker notes show up in pdfpc's presenter
  window with no `\note{}` conversion needed. Install pdfpc first: `sudo apt
  install pdfpc` (Debian/Ubuntu/WSL) or `brew install pdfpc` (macOS). ⚠️ pdfpc
  is a GTK dual-window GUI — on WSL2 it needs WSLg/an X server; simplest is to
  run it on the actual presentation laptop.
- [x] **Flip remaining "GPT-4o-mini" → "gpt-5.4-mini"** — DONE 2026-05-31
  session 2 (deck .tex + walkthrough script; live app already on gpt-5.4-mini).
- [x] **Regenerate the PPTX image backup** (`build_talk_pptx.py`) — DONE
  2026-05-31 session 2; now 33 slides.
- [x] **Send the Roxann title+abstract** — DONE (David emailed her the
  title + abstract from draft `r1539512532323228926`, 2026-06-01). Still TODO:
  email the deck PDF 1–2 days before 2026-06-11.
- [ ] **Trim to fit 45 min.** 33 frames ≈ ~1.3 min/slide is too tight; cut
  or merge before rehearsing. **OSINT stays and the unsupervised coda stays**
  (both kept per David 2026-05-28), so trim elsewhere — the quantum screenshots
  q01–q05 are the obvious candidates to thin.
- [ ] Screenshot the 2017 Springer paper landing page (DOI 10.1007/s10894-017-0123-4)
  → `slides/figures/openalex_screenshots/osint_roshan_paper.png` (the "payoff"
  slide has a placeholder box until then). Switched from the IPM seminar page
  2026-05-26 — that URL is geoblocked and unarchived; the paper is permanent.
- [ ] **Security-officer review** before presenting — now covers ONE module:
  the OSINT case study (slides make NO operational claims by design, but any
  framing of prior OSINT work as having produced outcomes needs separate
  clearance). *(The JNWC IQR backup section was REMOVED 2026-06-02, so the
  current-program EW content is no longer in the deck.)*

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
