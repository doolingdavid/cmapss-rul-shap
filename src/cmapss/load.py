"""Load the NASA CMAPSS Turbofan Engine Degradation Simulation dataset.

Saxena, A. and Goebel, K. (2008). "Turbofan Engine Degradation Simulation
Data Set", NASA Prognostics Data Repository, NASA Ames Research Center,
Moffett Field, CA.
https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/

Four subsets FD001-FD004 with different operating-condition and fault-mode
mixes. Each ``train_FDxxx.txt`` file is whitespace-delimited:

    unit  cycle  op_setting_1 op_setting_2 op_setting_3  sensor_1 ... sensor_21

One row per (engine, cycle). Engines are run to failure: the last cycle for
each unit is the failure cycle.

The companion ``test_FDxxx.txt`` files are *truncated* (engines stopped
some unknown number of cycles before failure) and ``RUL_FDxxx.txt`` lists
the true remaining cycles at the truncation point. Phase 1 of the talk
pipeline uses only ``train_FDxxx.txt`` and splits its engines 60/20/20.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests

# Standard column names per the data description PDF (Saxena & Goebel 2008,
# Table 1). The raw files have no header.
_RAW_COLUMNS = (
    ["unit", "cycle"]
    + [f"op_setting_{i}" for i in (1, 2, 3)]
    + [f"sensor_{i}" for i in range(1, 22)]
)

CMAPSS_COLUMN_NAMES = {
    "op_setting_1": "altitude",
    "op_setting_2": "mach_number",
    "op_setting_3": "throttle_resolver_angle",
    "sensor_1":  "fan_inlet_temp_T2",
    "sensor_2":  "lpc_outlet_temp_T24",
    "sensor_3":  "hpc_outlet_temp_T30",
    "sensor_4":  "lpt_outlet_temp_T50",
    "sensor_5":  "fan_inlet_pressure_P2",
    "sensor_6":  "bypass_duct_pressure_P15",
    "sensor_7":  "hpc_outlet_pressure_P30",
    "sensor_8":  "physical_fan_speed_Nf",
    "sensor_9":  "physical_core_speed_Nc",
    "sensor_10": "engine_pressure_ratio_epr",
    "sensor_11": "hpc_outlet_static_pressure_Ps30",
    "sensor_12": "fuel_flow_ratio_phi",
    "sensor_13": "corrected_fan_speed_NRf",
    "sensor_14": "corrected_core_speed_NRc",
    "sensor_15": "bypass_ratio_BPR",
    "sensor_16": "burner_fuel_air_ratio_farB",
    "sensor_17": "bleed_enthalpy_htBleed",
    "sensor_18": "demanded_fan_speed_Nf_dmd",
    "sensor_19": "demanded_corrected_fan_speed_PCNfR_dmd",
    "sensor_20": "hpt_coolant_bleed_W31",
    "sensor_21": "lpt_coolant_bleed_W32",
}

SUBSETS = ("FD001", "FD002", "FD003", "FD004")

# Public S3 mirror of the PHM datasets (NASA's own URLs have churned across
# .gov rebrands; this mirror has been stable). The zip contains all
# train/test/RUL files plus the data description PDF.
_MIRROR_URL = (
    "https://phm-datasets.s3.amazonaws.com/NASA/"
    "6.+Turbofan+Engine+Degradation+Simulation+Data+Set.zip"
)

_EPOCH = pd.Timestamp("2024-01-01 00:00:00")
_CYCLE_INTERVAL = pd.Timedelta(hours=1)


def download_cmapss(dest: str | Path = "data/cmapss", *, force: bool = False) -> Path:
    """Fetch the CMAPSS zip into ``dest`` and unpack the .txt + PDF files.

    Idempotent: returns immediately if ``train_FD001.txt`` already exists,
    unless ``force=True``. Falls back to a clear error pointing at the
    NASA PCOE page if the download fails.
    """
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    sentinel = dest / "train_FD001.txt"
    if sentinel.exists() and not force:
        return dest

    try:
        resp = requests.get(_MIRROR_URL, timeout=120)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(
            f"Could not download CMAPSS from {_MIRROR_URL!r}: {e}.\n"
            "Download manually from "
            "https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/ "
            f"and extract train_FDxxx.txt, test_FDxxx.txt, RUL_FDxxx.txt into {dest}."
        ) from e

    # The mirror ships a nested zip: outer/<folder>/CMAPSSData.zip → inner files.
    def _extract_data_files(zf: zipfile.ZipFile) -> int:
        n = 0
        for info in zf.infolist():
            name = Path(info.filename).name
            if not name:
                continue
            if name.lower().endswith((".txt", ".pdf")):
                (dest / name).write_bytes(zf.read(info))
                n += 1
            elif name.lower().endswith(".zip"):
                with zipfile.ZipFile(io.BytesIO(zf.read(info))) as inner:
                    n += _extract_data_files(inner)
        return n

    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        extracted = _extract_data_files(zf)
    if extracted == 0:
        raise RuntimeError(
            f"Downloaded zip from {_MIRROR_URL!r} but extracted no .txt/.pdf files."
        )
    return dest


def _attach_timestamp(df: pd.DataFrame) -> pd.DataFrame:
    """Add a synthetic pandas DatetimeIndex column, one hour per cycle.

    The per-engine timeline starts at ``_EPOCH`` for cycle 1 and advances
    one hour per cycle. CMAPSS cycles are unitless in the source data;
    a per-flight-hour convention makes the time axis legible in plots.
    """
    df = df.copy()
    df["timestamp"] = _EPOCH + (df["cycle"].astype("int64") - 1) * _CYCLE_INTERVAL
    return df


def read_subset(
    name: str,
    src: str | Path = "data/cmapss",
    *,
    rename: bool = True,
) -> pd.DataFrame:
    """Read one CMAPSS subset (``train_FDxxx.txt``) into a long-format DataFrame.

    Columns:
      - ``engine_id`` (int) — the original ``unit`` index, 1-based.
      - ``cycle`` (int) — 1-based per-engine cycle counter.
      - ``timestamp`` — synthetic datetime (cycle 1 == 2024-01-01 00:00, +1 h).
      - ``subset`` — the subset name (FD001-FD004), for cross-subset analyses.
      - 3 op-settings + 21 sensors, renamed to physical names per Saxena/Goebel
        when ``rename=True``.
    """
    if name not in SUBSETS:
        raise ValueError(f"unknown CMAPSS subset {name!r}; expected one of {SUBSETS}")
    path = Path(src) / f"train_{name}.txt"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run `download_cmapss({src!r})` or extract the "
            "PCOE zip manually."
        )

    df = pd.read_csv(path, sep=r"\s+", header=None, names=_RAW_COLUMNS, engine="python")
    df = df.rename(columns={"unit": "engine_id"})
    df["engine_id"] = df["engine_id"].astype("int32")
    df["cycle"] = df["cycle"].astype("int32")
    if rename:
        df = df.rename(columns=CMAPSS_COLUMN_NAMES)
    df = _attach_timestamp(df)
    df["subset"] = name
    # Stable ordering: engine, then cycle.
    df = df.sort_values(["engine_id", "cycle"]).reset_index(drop=True)
    return df


def read_all_subsets(
    src: str | Path = "data/cmapss",
    subsets: Iterable[str] = SUBSETS,
    *,
    rename: bool = True,
) -> dict[str, pd.DataFrame]:
    """Return one frame per subset, keyed by subset name."""
    return {s: read_subset(s, src, rename=rename) for s in subsets}


def feature_columns(df: pd.DataFrame) -> list[str]:
    """Names of the model-input columns (3 op-settings + 21 sensors).

    Works whether columns were renamed or not; excludes housekeeping
    (engine_id, cycle, timestamp, subset, RUL, y_*).
    """
    drop = {"engine_id", "cycle", "timestamp", "subset", "RUL"}
    return [c for c in df.columns if c not in drop and not c.startswith("y_")]
