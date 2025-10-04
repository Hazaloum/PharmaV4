import pandas as pd

# ─── 1/ Create combination column ──────────────────────────────────────────────
def create_combination_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds a 'Molecule Combination' column by grouping all molecules under each product.
    """
    df = df.copy()
    df["Molecule_upper"] = df["Molecule"].str.upper()
    df["Product_upper"]  = df["Product"].str.upper()
    combo_map = (
        df.groupby("Product_upper")["Molecule_upper"]
          .apply(lambda s: " + ".join(sorted(s.unique())))
          .to_dict()
    )
    df["Molecule Combination"] = df["Product_upper"].map(combo_map)
    df.drop(columns=["Molecule_upper", "Product_upper"], inplace=True)
    return df

# ─── 2/ Helpers for human-readable formatting ──────────────────────────────────
def human_fmt(x):
    if pd.isna(x): return "N/A"
    x = float(x)
    if abs(x) >= 1e6: return f"{x/1e6:.2f}M"
    if abs(x) >= 1e3: return f"{x/1e3:.2f}K"
    return f"{x:.0f}"

def currency_fmt(x):
    if pd.isna(x): return "AED N/A"
    x = float(x)
    if abs(x) >= 1e6: return f"AED {x/1e6:.2f}M"
    if abs(x) >= 1e3: return f"AED {x/1e3:.2f}K"
    return f"AED {x:,.0f}"

# ─── 3/ Core forecasting routines ───────────────────────────────────────────────
def forecast_molecule_product(
    df: pd.DataFrame,
    molecule_name: str,
    product_name: str,
    growth_rate: float = 0.10
) -> pd.DataFrame:
    """
    Forecasts Y1–Y3 units and revenue based on competitor-adjusted Y1 penetration.
    """
    mol = molecule_name.strip().upper()
    prod = product_name.strip().upper()

    df = df.copy()
    df = create_combination_column(df)
    df["Molecule Combination"] = df["Molecule Combination"].str.upper()
    df["Product"] = df["Product"].str.upper()

    # Subset product-molecule
    psub = df[(df["Molecule Combination"] == mol) & (df["Product"] == prod)].copy()
    if psub.empty:
        raise KeyError(f"No data for {mol} → {prod}")

    # Normalize combo molecules
    psub["n_mols"] = psub["Molecule Combination"].str.count(r" \+ ") + 1
    psub["2024 Units"] /= psub["n_mols"]

    mol_df = df[df["Molecule Combination"] == mol].copy()
    mol_df["n_mols"] = mol_df["Molecule Combination"].str.count(r" \+ ") + 1
    mol_df["2024 Units"] /= mol_df["n_mols"]
    mol_df["2024 LC Value"] = pd.to_numeric(mol_df["2024 LC Value"], errors="coerce").fillna(0)
    total_mol_2024_units = mol_df["2024 Units"].sum()
    total_mol_2024_value = mol_df["2024 LC Value"].sum()

    # Competitor-based penetration logic
    num_competitors = mol_df["Manufacturer"].nunique()
    if num_competitors == 1:
        penetration = 0.20
    elif 2 <= num_competitors <= 4:
        penetration = 0.10
    else:
        penetration = 0.05

    # Pack-level aggregation
    packs = (
        psub
        .groupby(["Pack", "Retail Price"], as_index=False)
        .agg(Pack_Units=("2024 Units", "sum"))
    )

    total_prod_units = packs["Pack_Units"].sum()
    packs["Pack Share"] = packs["Pack_Units"] / (total_prod_units or 1)

    # Forecast logic
    packs["Y1 Units"] = packs["Pack Share"] * total_mol_2024_units * penetration
    packs["Y2 Units"] = packs["Y1 Units"] * (1 + growth_rate)
    packs["Y3 Units"] = packs["Y2 Units"] * (1 + growth_rate)

    # Price logic
    packs["CIF Price"] = (packs["Retail Price"] / 1.4) * 0.4
    for y in ("Y1", "Y2", "Y3"):
        packs[f"{y} Revenue"] = packs[f"{y} Units"] * packs["CIF Price"]

    # Add context
    packs["Molecule"] = mol
    packs["Product"] = prod
    packs["Total 2024 Units"] = total_mol_2024_units
    packs["Total 2024 Value"] = total_mol_2024_value
    packs["Competitors"] = num_competitors
    packs["Penetration %"] = f"{penetration * 100:.0f}%"

    return packs[[
        "Molecule", "Product", "Total 2024 Units", "Total 2024 Value", "Competitors", "Penetration %",
        "Pack", "Pack_Units", "Pack Share",
        "Y1 Units", "Y2 Units", "Y3 Units",
        "Retail Price", "CIF Price",
        "Y1 Revenue", "Y2 Revenue", "Y3 Revenue"
    ]]

# ─── 4/ Pretty formatter ─────────────────────────────────────────────────────────
def forecast_molecule_product_fmt(
    df: pd.DataFrame,
    molecule_name: str,
    product_name: str,
    growth_rate: float = 0.2
) -> pd.DataFrame:
    raw = forecast_molecule_product(df, molecule_name, product_name, growth_rate=growth_rate)
    fmt = raw.copy()

    fmt["Total 2024 Units"] = fmt["Total 2024 Units"].apply(human_fmt)
    fmt["Total 2024 Value"] = fmt["Total 2024 Value"].apply(currency_fmt)
    fmt["Pack_Units"] = fmt["Pack_Units"].apply(human_fmt)
    fmt["Pack Share"] = fmt["Pack Share"].apply(lambda x: f"{x*100:.1f}%")

    for c in ("Y1 Units", "Y2 Units", "Y3 Units"):
        fmt[c] = fmt[c].apply(human_fmt)

    fmt["Retail Price"] = fmt["Retail Price"].apply(currency_fmt)
    fmt["CIF Price"] = fmt["CIF Price"].apply(currency_fmt)

    for c in ("Y1 Revenue", "Y2 Revenue", "Y3 Revenue"):
        fmt[c] = fmt[c].apply(currency_fmt)

    return fmt

def summarize_portfolio(forecast_list):
    """
    Accepts a list of forecast DataFrames (raw, not formatted),
    and returns a Markdown summary of total Y1–Y3 revenue.
    """
    if not forecast_list:
        return "❗ No forecasts to summarize."

    combined = pd.concat(forecast_list, ignore_index=True)
    
    total_y1 = combined["Y1 Revenue"].sum()
    total_y2 = combined["Y2 Revenue"].sum()
    total_y3 = combined["Y3 Revenue"].sum()

    def currency_fmt(x):
        if pd.isna(x): return "AED N/A"
        x = float(x)
        if abs(x) >= 1e6: return f"AED {x/1e6:.2f}M"
        if abs(x) >= 1e3: return f"AED {x/1e3:.2f}K"
        return f"AED {x:,.0f}"

    md = f"""
### 💼 Portfolio Forecast Summary

| Year | Total Forecasted Revenue |
|------|---------------------------|
| 📅 Y1 | **{currency_fmt(total_y1)}** |
| 📅 Y2 | **{currency_fmt(total_y2)}** |
| 📅 Y3 | **{currency_fmt(total_y3)}** |
"""
    return md