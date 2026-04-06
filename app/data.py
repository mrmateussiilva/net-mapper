import io
import re
from collections import defaultdict
from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st

from app.config import SHEETS, IGNORE


def safe(v) -> str:
    """Returns a stripped string version of v if non-NA, else empty string."""
    return str(v).strip() if pd.notna(v) else ""


def hascol(df: pd.DataFrame, c: str) -> bool:
    """Checks if a column exists in the DataFrame."""
    return c in df.columns


def ign(v) -> bool:
    """Checks if a string value should be ignored based on IGNORE list."""
    return str(v).strip().upper() in IGNORE


@st.cache_data(show_spinner=False)
def load_and_process_data(fb: bytes) -> Tuple[Dict[str, pd.DataFrame], pd.DataFrame]:
    """
    Loads Excel bytes, processes specific sheets, normalizes data,
    and returns a dictionary of dataframes per sheet and a combined dataframe.
    """
    dfs = {}
    for sheet in SHEETS:
        df = pd.read_excel(io.BytesIO(fb), sheet_name=sheet, header=5)
        df = df.iloc[:, 1:]
        df.columns = [str(c).strip() for c in df.columns]
        
        if "1" in df.columns:
            df = df.rename(columns={"1": "Rack"})
            
        if "Deck" in df.columns:
            # Safely filter out rows without Deck or literal "Deck" headers mixed in data
            df = df[df["Deck"].notna() & (df["Deck"].astype(str).str.strip() != "Deck")].reset_index(drop=True)

        def norm(v):
            v = str(v).strip().upper()
            if v in ("YES", "YES, YES", "YES,YES", "YES?", "1"):
                return "Active"
            if v in ("NO", "EMPTY"):
                return "Inactive/Empty"
            if v in ("XX", "XXX", "?", "XX,XX", "XX ,XX"):
                return "Unknown"
            if v == "NAN":
                return "Not Documented"
            return v

        if "Active" in df.columns:
            df["Active_norm"] = df["Active"].apply(norm)
        else:
            df["Active_norm"] = "Not Documented"

        if "Port" in df.columns:
            df["Port"] = pd.to_numeric(df["Port"], errors="coerce")

        dfs[sheet] = df

    all_df = pd.concat([df.assign(Deck=sh) for sh, df in dfs.items()], ignore_index=True)
    return dfs, all_df


@st.cache_data(show_spinner=False)
def detect_errors(df: pd.DataFrame, name: str) -> List[pd.DataFrame]:
    """
    Scans the dataframe for common errors and inconsistencies.
    Returns a list of dataframes containing the problematic rows.
    Cached to prevent recalculating on every render.
    """
    issues = []
    kc = ["Rack", "Optic Patch Painel", "Port"]
    if all(c in df.columns for c in kc):
        m = df.duplicated(subset=kc, keep=False) & df[kc].notna().all(axis=1)
        if m.any():
            d = df[m].copy()
            d["Issue"] = "Porta duplicada (Rack+PP+Port)"
            d["Sheet"] = name
            issues.append(d)
            
    if hascol(df, "Switch") and hascol(df, "Switch Port"):
        sub = df[
            df["Switch"].notna() & df["Switch Port"].notna() &
            ~df["Switch"].astype(str).str.upper().isin(["XXX", "XX", "NAN", "EMPTY"])
        ]
        dup = sub.duplicated(subset=["Switch", "Switch Port"], keep=False)
        if dup.any():
            d = sub[dup].copy()
            d["Issue"] = "Switch Port duplicada"
            d["Sheet"] = name
            issues.append(d)
            
    if hascol(df, "Active_norm"):
        act = df[df["Active_norm"] == "Active"]
        
        if hascol(df, "Switch"):
            bad = act[act["Switch"].isna() | act["Switch"].astype(str).str.upper().isin(["XXX", "XX", "EMPTY", "NAN"])]
            if not bad.empty:
                b = bad.copy()
                b["Issue"] = "Ativo sem Switch mapeado"
                b["Sheet"] = name
                issues.append(b)
                
        if hascol(df, "Wall Port"):
            bad = act[act["Wall Port"].astype(str).str.upper().isin(["XXX", "XX", "X"])]
            if not bad.empty:
                b = bad.copy()
                b["Issue"] = "Ativo: Wall Port = XXX"
                b["Sheet"] = name
                issues.append(b)
                
    if hascol(df, "Switch"):
        seen = defaultdict(list)
        for s in df["Switch"].dropna().astype(str).str.strip().unique():
            seen[re.sub(r"[\s_\-]", "", s).upper()].append(s)
            
        for k, names in seen.items():
            if len(names) > 1 and k not in IGNORE:
                d = df[df["Switch"].astype(str).str.strip().isin(names)].copy()
                d["Issue"] = f"Nome inconsistente: {names[:2]}"
                d["Sheet"] = name
                issues.append(d)
                
    return issues


@st.cache_data(show_spinner=False)
def health_score(df: pd.DataFrame, sheet_name: str) -> Tuple[int, str, Dict[str, float]]:
    """
    Computes a network health score for a given dataframe based on documentation,
    utilization, and absence of errors.
    """
    tot = max(len(df), 1)
    errs = sum(len(e) for e in detect_errors(df, sheet_name))
    
    if hascol(df, "Active_norm"):
        doc = (df["Active_norm"] != "Not Documented").sum() / tot
        act = (df["Active_norm"] == "Active").sum() / tot
        unk = 1 - (df["Active_norm"] == "Unknown").sum() / tot
    else:
        doc, act, unk = 0, 0, 0
        
    err_s = max(0.0, 1.0 - errs / max(tot * 0.1, 1))
    score = int((doc * 0.3 + act * 0.2 + unk * 0.3 + err_s * 0.2) * 100)
    grade = "A" if score >= 80 else "B" if score >= 60 else "C"
    
    return score, grade, {"Documentação": doc, "Utilização": act, "Mapeamento": unk, "Sem Erros": err_s}
