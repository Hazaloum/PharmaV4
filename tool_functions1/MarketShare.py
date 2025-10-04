import pandas as pd
import plotly.graph_objects as go

def plot_manufacturer_market_share(df, selected_molecule, market_type="PRIVATE MARKET"):
    df = df.copy()
    df.columns = df.columns.str.replace("\n", " ", regex=False).str.strip()
    df["Molecule Combination"] = df["Molecule Combination"].astype(str).str.upper().str.strip()
    selected_molecule = selected_molecule.strip().upper()

    mask = df["Molecule Combination"] == selected_molecule
    mol_df = df[mask]
    if market_type != "TOTAL":
        mol_df = mol_df[mol_df["Market"] == market_type]

    if mol_df.empty:
        return None

    years = ["2020", "2021", "2022", "2023", "2024"]
    unit_cols = [f"{y} Units" for y in years]

    grouped = mol_df.groupby("Manufacturer")[unit_cols].sum()
    grouped = grouped[grouped.sum(axis=1) > 0]

    # Calculate total per year for share
    total_units = grouped.sum(axis=0)

    fig = go.Figure()
    for mfr in grouped.index:
        shares = (grouped.loc[mfr] / total_units * 100).round(2)
        fig.add_trace(go.Scatter(
            x=years,
            y=shares.values,
            mode="lines+markers",
            name=mfr,
            hovertemplate=f"Manufacturer: {mfr}<br>" +
                          "Year: %{x}<br>" +
                          "Market Share: %{y}%<extra></extra>"
        ))

    fig.update_layout(
        title=f"📊 Market Share Over Time — {selected_molecule} ({market_type})",
        xaxis_title="Year",
        yaxis_title="Market Share (%)",
        template="plotly_white",
        height=500,
        legend_title="Manufacturer"
    )

    return fig