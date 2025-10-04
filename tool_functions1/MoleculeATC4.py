import pandas as pd
import plotly.graph_objects as go

def plotly_combinations_within_atc4_go(df, atc4_name, UseValue=True, years=None):
    def compute_cagr_safe(series, end_year, start_years=["2021", "2022", "2023"]):
        for y in start_years:
            start = series.get(f"{y} Units", 0) if not UseValue else series.get(f"{y} LC Value", 0)
            if start > 0:
                end = series.get(f"{end_year} Units", 0) if not UseValue else series.get(f"{end_year} LC Value", 0)
                n_years = int(end_year) - int(y)
                return ((end / start) ** (1 / n_years) - 1) * 100 if end > 0 else 0.0
        return 0.0

    if years is None:
        years = ["2021", "2022", "2023", "2024"]
    metric_label = "Value (AED)" if UseValue else "Units"
    end_year = years[-1]

    df = df.copy()
    df.columns = df.columns.str.replace("\n", " ", regex=False).str.strip()

    unit_cols  = [f"{y} Units"    for y in years]
    value_cols = [f"{y} LC Value" for y in years]
    metric_cols = value_cols if UseValue else unit_cols

    df_f = df[df["ATC4"] == atc4_name].copy()
    if df_f.empty:
        return None, None

    for c in unit_cols + value_cols:
        df_f[c] = pd.to_numeric(df_f[c], errors="coerce").fillna(0)

    # Count unique competitors per combination
    competitor_counts = df_f.groupby("Molecule Combination")["Manufacturer"].nunique()

    grp_units  = df_f.groupby("Molecule Combination")[unit_cols].sum()
    grp_values = df_f.groupby("Molecule Combination")[value_cols].sum()
    grp_metric = grp_values if UseValue else grp_units

    total_units  = grp_units.sum()
    total_values = grp_values.sum()
    total_metric = total_values if UseValue else total_units
    total_metric[total_metric == 0] = 1e-9

    pct_share = grp_metric.divide(total_metric, axis=1) * 100
    pct_share = pct_share.fillna(0).round(1)

    fig = go.Figure()
    for combo in grp_metric.index:
        y_raw = [grp_metric.at[combo, col] for col in metric_cols]
        y_pct = [pct_share.at[combo, col] for col in metric_cols]
        x_years = [c.split()[0] for c in metric_cols]

        series_u = grp_units.loc[combo]
        series_v = grp_values.loc[combo]
        u_cagr = compute_cagr_safe(series_u, end_year)
        v_cagr = compute_cagr_safe(series_v, end_year)

        fig.add_trace(go.Bar(
            name=combo,
            x=x_years,
            y=y_raw,
            customdata=[
                [
                    series_u.get(f"{years[0]} Units", 0),
                    series_u.get(f"{end_year} Units", 0),
                    series_v.get(f"{years[0]} LC Value", 0),
                    series_v.get(f"{end_year} LC Value", 0),
                    y_pct[i],
                    u_cagr,
                    v_cagr,
                    competitor_counts.get(combo, 0)
                ]
                for i in range(len(metric_cols))
            ],
            hovertemplate=(
                "<b>%{fullData.name}</b><br>"
                f"{metric_label}: " + "%{y:,.0f}<br>"
                "Market Share: %{customdata[4]:.1f}%<br>"
                "Unit CAGR: %{customdata[5]:.1f}%<br>"
                "Value CAGR: %{customdata[6]:.1f}%<br>"
                "Competitors: %{customdata[7]}<extra></extra>"
            )
        ))

    fig.update_layout(
        barmode="stack",
        title=f"Combination Breakdown — {atc4_name} ({years[0]}–{end_year})",
        xaxis_title="Year",
        yaxis_title=metric_label,
        legend_title="Combination",
        height=600,
        width=1000
    )

    # Summary table
    rows = []
    for combo in grp_metric.index:
        series_u = grp_units.loc[combo]
        series_v = grp_values.loc[combo]
        u_end = int(series_u.get(f"{end_year} Units", 0))
        v_end = int(series_v.get(f"{end_year} LC Value", 0))
        share = pct_share.at[combo, f"{end_year} LC Value"] if UseValue else pct_share.at[combo, f"{end_year} Units"]
        u_cagr = compute_cagr_safe(series_u, end_year)
        v_cagr = compute_cagr_safe(series_v, end_year)
        n_competitors = competitor_counts.get(combo, 0)

        rows.append({
            "Combination": combo,
            f"{end_year} Units": u_end,
            f"{end_year} Value (AED)": v_end,
            "Share (%)": round(share, 1),
            "Units CAGR (%)": round(u_cagr, 1),
            "Value CAGR (%)": round(v_cagr, 1),
            "Competitors": n_competitors
        })

    summary_df = pd.DataFrame(rows)\
                   .sort_values(by=f"{end_year} {'Value (AED)' if UseValue else 'Units'}", ascending=False)\
                   .reset_index(drop=True)

    # Optional debug: Top gainers and losers
    sort_cagr_col = "Value CAGR (%)" if UseValue else "Units CAGR (%)"
    summary_sorted = summary_df.sort_values(by=sort_cagr_col, ascending=False)

    top_5_winners = summary_sorted.head(5).copy()
    top_5_losers = summary_sorted.tail(5).copy()

    print("🏆 Top 5 Winners by CAGR:")
    print(top_5_winners[["Combination", sort_cagr_col]])

    print("\n📉 Top 5 Losers by CAGR:")
    print(top_5_losers[["Combination", sort_cagr_col]])

    return fig, summary_df