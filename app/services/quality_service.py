import re
from collections import defaultdict
from typing import Dict, List, Tuple

import pandas as pd

from app.config import IGNORE
from app.services.mapping_service import hascol


def detect_errors(df: pd.DataFrame, name: str) -> List[pd.DataFrame]:
    """Scan the dataframe for common mapping inconsistencies."""
    issues = []
    key_cols = ["Rack", "Optic Patch Painel", "Port"]
    if all(c in df.columns for c in key_cols):
        duplicated = df.duplicated(subset=key_cols, keep=False) & df[key_cols].notna().all(axis=1)
        if duplicated.any():
            data = df[duplicated].copy()
            data["Issue"] = "Porta duplicada (Rack+PP+Port)"
            data["Sheet"] = name
            issues.append(data)

    if hascol(df, "Switch") and hascol(df, "Switch Port"):
        subset = df[
            df["Switch"].notna() & df["Switch Port"].notna() &
            ~df["Switch"].astype(str).str.upper().isin(["XXX", "XX", "NAN", "EMPTY"])
        ]
        duplicated = subset.duplicated(subset=["Switch", "Switch Port"], keep=False)
        if duplicated.any():
            data = subset[duplicated].copy()
            data["Issue"] = "Switch Port duplicada"
            data["Sheet"] = name
            issues.append(data)

    if hascol(df, "Active_norm"):
        active = df[df["Active_norm"] == "Active"]

        if hascol(df, "Switch"):
            bad_switch = active[
                active["Switch"].isna() |
                active["Switch"].astype(str).str.upper().isin(["XXX", "XX", "EMPTY", "NAN"])
            ]
            if not bad_switch.empty:
                data = bad_switch.copy()
                data["Issue"] = "Ativo sem Switch mapeado"
                data["Sheet"] = name
                issues.append(data)

        if hascol(df, "Wall Port"):
            bad_wall_port = active[active["Wall Port"].astype(str).str.upper().isin(["XXX", "XX", "X"])]
            if not bad_wall_port.empty:
                data = bad_wall_port.copy()
                data["Issue"] = "Ativo: Wall Port = XXX"
                data["Sheet"] = name
                issues.append(data)

    if hascol(df, "Switch"):
        seen = defaultdict(list)
        for switch in df["Switch"].dropna().astype(str).str.strip().unique():
            seen[re.sub(r"[\s_\-]", "", switch).upper()].append(switch)

        for normalized, names in seen.items():
            if len(names) > 1 and normalized not in IGNORE:
                data = df[df["Switch"].astype(str).str.strip().isin(names)].copy()
                data["Issue"] = f"Nome inconsistente: {names[:2]}"
                data["Sheet"] = name
                issues.append(data)

    return issues


def health_score(df: pd.DataFrame, sheet_name: str) -> Tuple[int, str, Dict[str, float]]:
    """Compute a network health score based on documentation, usage and mapping quality."""
    total = max(len(df), 1)
    errors = sum(len(issue) for issue in detect_errors(df, sheet_name))

    if hascol(df, "Active_norm"):
        documentation = (df["Active_norm"] != "Not Documented").sum() / total
        utilization = (df["Active_norm"] == "Active").sum() / total
        mapping = 1 - (df["Active_norm"] == "Unknown").sum() / total
    else:
        documentation, utilization, mapping = 0.0, 0.0, 0.0

    no_errors = max(0.0, 1.0 - errors / max(total * 0.1, 1))
    score = int((documentation * 0.3 + utilization * 0.2 + mapping * 0.3 + no_errors * 0.2) * 100)
    grade = "A" if score >= 80 else "B" if score >= 60 else "C"

    return score, grade, {
        "Documentação": documentation,
        "Utilização": utilization,
        "Mapeamento": mapping,
        "Sem Erros": no_errors,
    }
