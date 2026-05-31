"""
indicators/macro_merge.py
─────────────────────────
Inject macro covariates (DXY, Funding Rate, Open Interest) into any
strategy dataframe via backward timestamp-aligned merge.

Single canonical implementation — replaces the copy-pasted version that
existed in every strategy file.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd
from pandas import DataFrame

logger = logging.getLogger(__name__)

_BASE = Path(__file__).resolve().parent.parent
_MACRO_FILE = _BASE / "risk" / "macro_history.json"
_MACRO_COLS = ["dxy_24h_change", "btc_funding_rate", "btc_open_interest"]


def merge_macro_data(dataframe: DataFrame) -> DataFrame:
    """
    Merge macro covariates into a strategy OHLCV dataframe.

    Uses pd.merge_asof (backward) so each candle gets the most recent
    macro snapshot without look-ahead bias.  Returns the original
    dataframe with zeroed macro columns on any failure.
    """
    try:
        if not _MACRO_FILE.exists():
            for col in _MACRO_COLS:
                dataframe[col] = 0.0
            return dataframe

        with open(_MACRO_FILE) as f:
            history = json.load(f)

        macro_df = pd.DataFrame(history)
        macro_df["date"] = pd.to_datetime(macro_df["timestamp"], format="ISO8601")
        macro_df = macro_df.sort_values("date")

        dataframe = dataframe.sort_values("date")
        dataframe = pd.merge_asof(
            dataframe,
            macro_df[["date"] + _MACRO_COLS],
            on="date",
            direction="backward",
        )
        dataframe[_MACRO_COLS] = dataframe[_MACRO_COLS].fillna(0.0)
        return dataframe

    except Exception:
        logger.debug("merge_macro_data failed silently — zeroing macro cols")
        for col in _MACRO_COLS:
            if col not in dataframe.columns:
                dataframe[col] = 0.0
        return dataframe
