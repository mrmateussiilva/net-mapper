import io
from typing import Dict, Tuple

import pandas as pd

from app.config import IGNORE, SHEETS


def safe(v) -> str:
    """Return a stripped string version of v if non-NA, else empty string."""
    return str(v).strip() if pd.notna(v) else ""


def hascol(df: pd.DataFrame, c: str) -> bool:
    """Check if a column exists in the DataFrame."""
    return c in df.columns


def ign(v) -> bool:
    """Check if a string value should be ignored based on IGNORE."""
    return str(v).strip().upper() in IGNORE


def normalize_active(value) -> str:
    """Normalize spreadsheet status values into canonical labels."""
    normalized = str(value).strip().upper()
    if normalized in ("YES", "YES, YES", "YES,YES", "YES?", "1"):
        return "Active"
    if normalized in ("NO", "EMPTY"):
        return "Inactive/Empty"
    if normalized in ("XX", "XXX", "?", "XX,XX", "XX ,XX"):
        return "Unknown"
    if normalized == "NAN":
        return "Not Documented"
    return normalized


def load_and_process_data(fb: bytes) -> Tuple[Dict[str, pd.DataFrame], pd.DataFrame]:
    """
    Load Excel bytes, process expected sheets and return deck dataframes plus a combined dataframe.
    """
    dfs: Dict[str, pd.DataFrame] = {}
    for sheet in SHEETS:
        df = pd.read_excel(io.BytesIO(fb), sheet_name=sheet, header=5)
        df = df.iloc[:, 1:]
        df.columns = [str(c).strip() for c in df.columns]

        if "1" in df.columns:
            df = df.rename(columns={"1": "Rack"})

        if "Deck" in df.columns:
            df = df[df["Deck"].notna() & (df["Deck"].astype(str).str.strip() != "Deck")].reset_index(drop=True)

        if "Active" in df.columns:
            df["Active_norm"] = df["Active"].apply(normalize_active)
        else:
            df["Active_norm"] = "Not Documented"

        if "Port" in df.columns:
            df["Port"] = pd.to_numeric(df["Port"], errors="coerce")

        dfs[sheet] = df

    all_df = pd.concat([df.assign(Deck=sheet) for sheet, df in dfs.items()], ignore_index=True)
    return dfs, all_df
