import pandas as pd

def generate_molecule_overview(df, molecule_name):
    """
    Returns a clean, formatted vertical summary DataFrame for a given molecule.
    """
    m = molecule_name.strip().upper()
    mol_df = df[df["Molecule Combination"].str.upper() == m]
    if mol_df.empty:
        return None

    # Helper: CAGR
    def cagr(start, end, n=4):
        if start > 0 and end > 0:
            try:
                return ((end / start) ** (1 / n) - 1) * 100
            except:
                return 0
        return 0

    # ATC info
    atc3 = mol_df["ATC3"].mode()[0] if not mol_df["ATC3"].isna().all() else "N/A"
    atc4 = mol_df["ATC4"].mode()[0] if not mol_df["ATC4"].isna().all() else "N/A"
    atc4_df = df[df["ATC4"] == atc4]
    atc3_df = df[df["ATC3"] == atc3]

    # Yearly values
    years = ["2021", "2022", "2023", "2024"]
    units = [mol_df[f"{y} Units"].sum() for y in years]
    values = [mol_df[f"{y} LC Value"].sum() for y in years]

    # CAGR calculations
    units_cagr = cagr(units[0], units[-1])
    value_cagr = cagr(values[0], values[-1])
    atc4_cagr = cagr(atc4_df["2021 LC Value"].sum(), atc4_df["2024 LC Value"].sum())
    atc3_cagr = cagr(atc3_df["2021 LC Value"].sum(), atc3_df["2024 LC Value"].sum())

    # Market stats
    competitors = atc4_df["Molecule Combination"].nunique() - 1
    manuf_df = mol_df.groupby("Manufacturer")["2024 Units"].sum().reset_index(name="units_2024")
    manuf_total = manuf_df["Manufacturer"].nunique()
    manuf_df["share"] = manuf_df["units_2024"] / (units[-1] or 1) * 100
    manuf_3pct = manuf_df[manuf_df["share"] >= 3]["Manufacturer"].nunique()

    # Launch year
    launch_year = int(mol_df["Launch Year"].min()) if not mol_df["Launch Year"].isna().all() else "N/A"

    # Private market shift
    private_2021 = mol_df[mol_df["Market"] == "PRIVATE MARKET"]["2021 Units"].sum()
    private_2024 = mol_df[mol_df["Market"] == "PRIVATE MARKET"]["2024 Units"].sum()
    private_pct_21 = private_2021 / (units[0] or 1) * 100
    private_pct_24 = private_2024 / (units[-1] or 1) * 100
    private_delta = private_pct_24 - private_pct_21

    # Final summary dictionary
    summary = {
        "2024 Units": units[-1],
        "2024 Value (AED)": values[-1],
        "Units CAGR (21→24) (%)": units_cagr,
        "Value CAGR (21→24) (%)": value_cagr,
        "Competitors in ATC4": competitors,
        "Manufacturers (Total)": manuf_total,
        "Manufacturers ≥3% Share": manuf_3pct,
        "First Launch Year": launch_year,
        "Private Market Share 2024 (%)": private_pct_24,
        "Private Market Shift (21→24) (%)": private_delta,
        "ATC4 Value 2024 (AED)": atc4_df["2024 LC Value"].sum(),
        "ATC4 Value CAGR (%)": atc4_cagr,
        "ATC3 Value 2024 (AED)": atc3_df["2024 LC Value"].sum(),
        "ATC3 Value CAGR (%)": atc3_cagr,
    }

    # Formatting helper
    def fmt(x):
        if isinstance(x, (int, float)):
            return f"{x:,.1f}"
        return x

    summary_df = pd.DataFrame(list(summary.items()), columns=["Metric", "Value"])
    summary_df["Value"] = summary_df["Value"].map(fmt)
    return summary_df