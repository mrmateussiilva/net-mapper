import pandas as pd

path = "Network Mapping - Safe Notos.xlsx"
sheets = ["Deck B - L717", "Deck M - L521", "Deck M - L519"]
IGNORE = {"NAN","XXX","XX","X","EMPTY","?",""}

for sheet in sheets:
    df = pd.read_excel(path, sheet_name=sheet, header=5)
    df = df.iloc[:, 1:]
    df.columns = [str(c).strip() for c in df.columns]
    if "1" in df.columns:
        df = df.rename(columns={"1": "Rack"})

    print(f"\n========== {sheet} ==========")

    if "Rack" in df.columns:
        racks = [r for r in df["Rack"].dropna().astype(str).str.strip().unique() if r not in IGNORE]
        print(f"  Racks ({len(racks)}): {racks[:10]}")

    if "Switch" in df.columns:
        sws = [s for s in df["Switch"].dropna().astype(str).str.strip().unique() if s.upper() not in IGNORE]
        print(f"  Switches ({len(sws)}): {sws[:10]}")

    if "Optic Patch Painel" in df.columns:
        pps = df["Optic Patch Painel"].dropna().astype(str).str.strip().unique()
        print(f"  Patch Panels ({len(pps)}): {list(pps[:8])}")

    if "Switch Port" in df.columns:
        sp = df["Switch Port"].dropna().astype(str).str.strip().unique()
        print(f"  Switch Port samples: {list(sp[:10])}")

    if "Active" in df.columns:
        print(f"  Active values: {df['Active'].value_counts().to_dict()}")

    key_cols = ["Rack","Optic Patch Painel","Port","Switch","Switch Port"]
    key_avail = [c for c in key_cols if c in df.columns]
    complete = df[key_avail].dropna()
    if "Switch" in complete.columns:
        complete = complete[~complete["Switch"].astype(str).str.upper().isin(IGNORE)]
    print(f"  Rows with full connection data: {len(complete)} / {len(df)}")

    if all(c in df.columns for c in ["Rack","Optic Patch Painel","Port"]):
        dups = df.duplicated(subset=["Rack","Optic Patch Painel","Port"], keep=False)
        print(f"  Duplicate Rack+PP+Port rows: {dups.sum()}")

    extra = [c for c in df.columns if "Unnamed" in c]
    for ec in extra:
        non_null = df[ec].dropna()
        if not non_null.empty:
            samples = list(non_null.astype(str).unique()[:5])
            print(f"  [{ec}] non-null={len(non_null)}, samples={samples}")
