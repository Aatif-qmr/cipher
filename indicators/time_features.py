"""
indicators/time_features.py
────────────────────────────
Add calendar / time-of-day features to a FreqAI feature dataframe.
Normalised to [0, 1] so all features are on the same scale.
"""

from __future__ import annotations

from pandas import DataFrame


def add_time_features(dataframe: DataFrame, prefix: str = "%-") -> DataFrame:
    """
    Add day-of-week and hour-of-day as normalised features.

    Columns added:
        {prefix}day_of_week  — 0.0 (Mon) … 1.0 (Sun)
        {prefix}hour_of_day  — 0.0 (00:00) … 1.0 (23:00)
    """
    dataframe[f"{prefix}day_of_week"] = dataframe["date"].dt.dayofweek / 6.0
    dataframe[f"{prefix}hour_of_day"] = dataframe["date"].dt.hour / 23.0
    return dataframe
