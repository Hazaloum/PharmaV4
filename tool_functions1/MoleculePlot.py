import pandas as pd
import plotly.graph_objects as go

def compute_cagr_dynamic(start_values: list, end: float, years: list) -> float:
    try:
        for i, start in enumerate(start_values):
            if start > 0 and not pd.isna(start):
                n = years[-1] - years[i]
                return ((end / start) ** (1 / n) - 1) * 100
        return 0.0
    except:
        return 0.0

def plot_combination_market_breakdown_plotly(
    df,
    selected_molecule,
    use_market_filter=True,
    market_type="PRIVATE MARKET",
    use_value=False,
    group_by_column="Manufacturer"
):
    selected_molecule = selected_molecule.strip().upper()
    df = df.copy()
    df["Market"] = df["Market"].astype(str).str.strip().str.upper()

    # --- Clean & numericize ---
    df.columns = df.columns.str.replace("\n", " ", regex=False).str.strip()
    df = df.rename(columns={"2020* Units": "2020 Units", "2020* LC Value": "2020 LC Value"})
    for col in df.columns:
        if "Value" in col or "Units" in col:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", "").str.strip(),
                errors="coerce"
            ).fillna(0)

    # --- Adjust values to avoid double-counting combo molecules ---
    df["Molecule Count"] = df["Molecule Combination"].str.count(r"\+") + 1
    for col in df.columns:
        if "Units" in col or "Value" in col:
            df[col] = df[col] / df["Molecule Count"]

    years = ["2020", "2021", "2022", "2023", "2024"]
    col_units = [f"{y} Units" for y in years]
    col_value = [f"{y} LC Value" for y in years]

    # --- Filter molecule & market ---
    mask = df["Molecule Combination"].str.upper() == selected_molecule
    molecule_df_all = df[mask]
    if use_market_filter:
        mol_df = molecule_df_all[molecule_df_all["Market"] == market_type.upper()]
    else:
        mol_df = molecule_df_all.copy()

    if group_by_column not in mol_df.columns:
        return None, None

    # --- Build product lookup per group ---
    product_map = (
        mol_df
        .groupby(group_by_column)["Product"]
        .unique()
        .apply(lambda arr: ", ".join(arr))
        .to_dict()
    )

    # --- Aggregate data ---
    grouped_units = mol_df.groupby(group_by_column)[col_units].sum()
    grouped_values = mol_df.groupby(group_by_column)[col_value].sum()

    # filter and sort
    grouped_units = grouped_units[grouped_units.sum(axis=1) > 0]
    grouped_values = grouped_values[grouped_values.sum(axis=1) > 0]
    exporters = sorted(
        set(grouped_units.index) & set(grouped_values.index),
        key=lambda g: grouped_values.loc[g, "2024 LC Value"],
        reverse=True
    )
    grouped_units = grouped_units.loc[exporters]
    grouped_values = grouped_values.loc[exporters]

    # --- Plotly figure ---
    fig = go.Figure()
    total_vals = grouped_values.sum(axis=0).values
    total_units = grouped_units.sum(axis=0).values

    for grp in exporters:
        y_vals = grouped_values.loc[grp].values if use_value else grouped_units.loc[grp].values
        shares = (y_vals / (total_vals if use_value else total_units) * 100).round(1)
        hover = [
            f"Year: {years[i]}<br>"
            f"{group_by_column}: {grp}<br>"
            f"Product: {product_map.get(grp, '')}<br>"
            f"Units: {grouped_units.loc[grp, f'{years[i]} Units']:,}<br>"
            f"Value: {grouped_values.loc[grp, f'{years[i]} LC Value']:,}<br>"
            f"Market Share: {shares[i]:.1f}%<br>"
            f"Units CAGR: {round(compute_cagr_dynamic([grouped_units.loc[grp, f'{y} Units'] for y in [2021, 2022, 2023]], grouped_units.loc[grp, '2024 Units'], [2021, 2022, 2023, 2024]), 1):.1f}%<br>"
            f"Value CAGR: {round(compute_cagr_dynamic([grouped_values.loc[grp, f'{y} LC Value'] for y in [2021, 2022, 2023]], grouped_values.loc[grp, '2024 LC Value'], [2021, 2022, 2023, 2024]), 1):.1f}%<extra></extra>"
            for i in range(len(years))
        ]
        fig.add_trace(go.Bar(
            name=str(grp),
            x=years,
            y=y_vals,
            hovertemplate=hover
        ))

    fig.update_layout(
        barmode='stack',
        title=f"{selected_molecule} — {market_type if use_market_filter else 'TOTAL'} by {group_by_column}",
        xaxis_title="Year",
        yaxis_title="Value (AED)" if use_value else "Units Sold",
        legend_title=group_by_column,
        height=600,
        template="plotly_white"
    )

    # Add annotation for total 2024 value
    total_2024_value = grouped_values["2024 LC Value"].sum()
    fig.add_annotation(
        text=f"<b>Total 2024 Value:</b> AED {total_2024_value:,.0f}",
        xref="paper", yref="paper",
        x=0, y=-0.2, showarrow=False,
        font=dict(size=20)
    )

    # --- Summary table ---

    rows = []
    for grp in exporters:
        val_2024 = grouped_values.loc[grp, "2024 LC Value"]
        share = val_2024 / (total_2024_value or 1) * 100
        rows.append({
            "Manufacturer": grp,
            "Product": product_map.get(grp, ''),
            "Value (2024 AED)": int(val_2024),
            "Units (2024)": int(grouped_units.loc[grp, "2024 Units"]),
            "Market Share (%)": round(share, 1),
            "Value CAGR (%)": round(compute_cagr_dynamic(
                [grouped_values.loc[grp, f"{y} LC Value"] for y in [2021, 2022, 2023]],
                val_2024,
                [2021, 2022, 2023, 2024]
            ), 1),
            "Units CAGR (%)": round(compute_cagr_dynamic(
                [grouped_units.loc[grp, f"{y} Units"] for y in [2021, 2022, 2023]],
                grouped_units.loc[grp, "2024 Units"],
                [2021, 2022, 2023, 2024]
            ), 1)
        })

    summary_df = pd.DataFrame(rows)

    return fig, summary_df

def generate_growth_by_column_card(df, combo, group_col, start_year=2021, end_year=2024):
    """
    Generates a mini growth summary card by NFC3 or Strength for a given molecule combination.
    """
    # Filter to selected molecule
    mol_df = df[df["Molecule Combination"].str.upper() == combo.upper()].copy()

    # Clean and parse values
    for year in [start_year, end_year]:
        for metric in ["Units", "LC Value"]:
            col = f"{year} {metric}"
            mol_df[col] = pd.to_numeric(
                mol_df[col].astype(str).str.replace(",", ""), errors="coerce"
            ).fillna(0)

    # Compute aggregates
    grouped = (
        mol_df.groupby(group_col)[
            [f"{start_year} Units", f"{end_year} Units", f"{start_year} LC Value", f"{end_year} LC Value"]
        ]
        .sum()
        .reset_index()
    )

    total_2024_value = grouped[f"{end_year} LC Value"].sum()
    grouped["Value %"] = grouped[f"{end_year} LC Value"] / (total_2024_value or 1) * 100
    grouped["Unit CAGR"] = (
        (grouped[f"{end_year} Units"] / (grouped[f"{start_year} Units"] + 1e-9)) ** (1 / (end_year - start_year)) - 1
    ) * 100
    grouped["Value CAGR"] = (
        (grouped[f"{end_year} LC Value"] / (grouped[f"{start_year} LC Value"] + 1e-9)) ** (1 / (end_year - start_year)) - 1
    ) * 100

    # Format for display
    grouped = grouped.sort_values("Value %", ascending=False).head(10)  # Top 10 entries
    md = f"#### 📊 Market Growth by {group_col}\n\n"
    md += "| " + group_col + " | % of Value | Unit CAGR | Value CAGR |\n"
    md += "|---|------------:|------------:|-------------:|\n"
    for _, row in grouped.iterrows():
        md += f"| {row[group_col]} | {row['Value %']:.1f}% | {row['Unit CAGR']:.1f}% | {row['Value CAGR']:.1f}% |\n"
    return md