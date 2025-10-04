import pandas as pd
import numpy as np
import plotly.graph_objects as go

def plot_market_erosion(df, molecule):
    df = df.copy()
    df["Molecule"] = df["Molecule"].astype(str).str.strip().str.upper()
    df["Molecule Combination"] = df.groupby("Product")["Molecule"].transform(
        lambda x: " + ".join(sorted(x.unique()))
    )

    for col in df.columns:
        if "Units" in col:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="coerce").fillna(0)

    mol_df = df[df["Molecule Combination"].str.upper() == molecule.upper()].copy()
    if mol_df.empty:
        return None, None

    atc4_code = mol_df["ATC4"].dropna().unique()[0]
    atc4_df = df[df["ATC4"] == atc4_code].copy()

    years = [2020, 2021, 2022, 2023, 2024]
    total_units_by_year = {y: mol_df[f"{y} Units"].sum() for y in years}

    manufacturer_totals = mol_df.groupby("Manufacturer")[["2021 Units", "2024 Units"]].sum()
    top_manufacturer = manufacturer_totals["2024 Units"].idxmax()
    top_2021 = manufacturer_totals.loc[top_manufacturer, "2021 Units"]
    top_2024 = manufacturer_totals.loc[top_manufacturer, "2024 Units"]
    total_2021 = mol_df["2021 Units"].sum()
    total_2024 = mol_df["2024 Units"].sum()
    originator_share_2021 = top_2021 / total_2021 if total_2021 > 0 else 0
    originator_share_2024 = top_2024 / total_2024 if total_2024 > 0 else 0
    erosion_percent = (originator_share_2021 - originator_share_2024) * 100

    erosion_drops = []
    avg_21_shares = []
    avg_24_shares = []

    for combo in atc4_df["Molecule Combination"].dropna().unique():
        temp_df = atc4_df[atc4_df["Molecule Combination"] == combo]
        manufacturers = temp_df["Manufacturer"].nunique()
        total_2024 = temp_df["2024 Units"].sum()
        top_2024_share = (
            temp_df.groupby("Manufacturer")["2024 Units"].sum().max() / total_2024
            if total_2024 > 0 else 1
        )
        if manufacturers <= 1 or top_2024_share >= 0.99:
            continue

        mfg_totals = temp_df.groupby("Manufacturer")[["2021 Units", "2024 Units"]].sum()
        top_manuf = mfg_totals["2024 Units"].idxmax()
        top_21 = mfg_totals.loc[top_manuf, "2021 Units"]
        top_24 = mfg_totals.loc[top_manuf, "2024 Units"]
        total_21 = temp_df["2021 Units"].sum()
        total_24 = temp_df["2024 Units"].sum()
        if total_21 > 0 and total_24 > 0:
            share_2021 = top_21 / total_21
            share_2024 = top_24 / total_24
            drop_pct = (share_2021 - share_2024) * 100
            if drop_pct > 0:
                erosion_drops.append(drop_pct)
                avg_21_shares.append(share_2021)
                avg_24_shares.append(share_2024)

    average_atc4_erosion = np.mean(erosion_drops) if erosion_drops else 0
    avg_originator_2021 = np.mean(avg_21_shares) if avg_21_shares else 0
    avg_originator_2024 = np.mean(avg_24_shares) if avg_24_shares else 0

    capture_data = []
    for manufacturer in mol_df["Manufacturer"].unique():
        man_df = mol_df[mol_df["Manufacturer"] == manufacturer]
        shares = []
        first_year = None
        for y in years:
            units = man_df[f"{y} Units"].sum()
            total = total_units_by_year[y]
            share = units / total if total > 0 else 0
            shares.append(share)
            if units > 0 and first_year is None:
                first_year = y
        if first_year is not None and first_year < 2024:
            years_since_entry = [y - first_year for y in years if y >= first_year]
            shares_since_entry = shares[years.index(first_year):]
            for yr, sh in zip(years_since_entry, shares_since_entry):
                capture_data.append({
                    "Manufacturer": manufacturer,
                    "Years Since Entry": yr,
                    "Market Share": sh * 100
                })

    capture_df = pd.DataFrame(capture_data)
    fig = go.Figure()
    for manu in capture_df["Manufacturer"].unique():
        sub_df = capture_df[capture_df["Manufacturer"] == manu]
        fig.add_trace(go.Scatter(
            x=sub_df["Years Since Entry"],
            y=sub_df["Market Share"],
            mode="lines+markers",
            name=manu,
            hovertemplate="Manufacturer: %{text}<br>Year Since Entry: %{x}<br>Market Share: %{y:.2f}%<extra></extra>",
            text=[manu]*len(sub_df)
        ))

    fig.update_layout(
        title=f"Market Share Growth After Entry – {molecule.upper()}",
        xaxis_title="Years Since Entry",
        yaxis_title="Market Share (%)",
        height=600,
        template="plotly_white"
    )

    erosion_stats = {
        "originator_2021": originator_share_2021,
        "originator_2024": originator_share_2024,
        "drop": erosion_percent,
        "average_atc4_erosion": average_atc4_erosion,
        "avg_originator_2021": avg_originator_2021,
        "avg_originator_2024": avg_originator_2024,
        "atc4_code": atc4_code
    }

    return fig, erosion_stats