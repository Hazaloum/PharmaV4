import streamlit as st
import pandas as pd

from tool_functions1.combinations      import create_combination_column
from tool_functions1.summary           import generate_molecule_overview
from tool_functions1.PacksAndProducts  import generate_combination_first_clean_summary
from tool_functions1.MohapLandscape    import format_registered_products_by_company
from tool_functions1.MoleculePlot      import plot_combination_market_breakdown_plotly, generate_growth_by_column_card
from tool_functions1.MoleculeATC4      import plotly_combinations_within_atc4_go
#from tool_functions.OrangeBook import generate_uptake_patent_view
from tool_functions1.SummaryGen import generate_exec_summary_data
from tool_functions1.MarketShare import plot_manufacturer_market_share
from tool_functions1.Erosion import plot_market_erosion
from tool_functions1.OrangeBook import display_patent_summary
from tool_functions1.Reg import get_regulatory_summary
from tool_functions1.DetailedForecast import create_combination_column, forecast_molecule_product_fmt
# --- Load Master Data ---
@st.cache_data
def load_master_data():
    df = pd.read_csv("MasterData2025.csv")

    # Clean column names early to avoid hidden '\n' or trailing spaces
    df.columns = df.columns.str.replace("\n", " ", regex=False).str.strip()

    # Normalize molecule and product columns BEFORE creating combination column
    df["Molecule"] = df["Molecule"].astype(str).str.strip().str.upper()
    df["Product"] = df["Product"].astype(str).str.strip().str.upper()

    # Create 'Molecule Combination' and 'Molecule Combination Type'
    df = create_combination_column(df)

    # Final clean of numeric columns
    for col in df.columns:
        if "Value" in col or "Units" in col:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", "").str.strip(),
                errors="coerce"
            )

    return df

# --- Load MOHAP Data ---
@st.cache_data
def load_mohap_data():
    mohap_df = pd.read_csv("PriceListMOHAP.csv")
    mohap_df.columns = mohap_df.columns.str.replace("\n", " ", regex=False).str.strip()


    return mohap_df


# --- Load data ---
df = load_master_data()
mohap_df = load_mohap_data()


# ── Compute top-seller per Molecule Combination ────────────────────────────────
combo_prod_sales = (
    df.groupby(["Molecule Combination", "Product"])["2024 Units"]
      .sum()
)
# for each combo, pick the (combo,product) with max units
top_pairs = combo_prod_sales.groupby(level=0).idxmax().tolist()
# build lookup dict: { combo: top_product }
top_product_for_combo = { combo: prod for combo, prod in top_pairs }


# --- UI ---
st.title("💊 UAE Molecule Intelligence Platform")

# Shared molecule selector
selected_combo = st.selectbox(
    "🔎 Search Molecule:",
    sorted(df["Molecule Combination"].dropna().unique())
)

# Tabs
tab1a, tab1b, tab_nfc3_growth, tab2, tab3, tab4, tab5, tab6, tab7, tab_batch = st.tabs([
    "📊 Exec Summary",
    "📈 Graph + Table",
    "📈 NFC3 + Strength Growth",
    "🔍 ATC4 Breakdown",
    "📋 Summary + Packs",
    "🏛️ MOHAP Insights",
    "📅 Patent Expiry Finder",
    "📉 Erosion & Uptake",
    "🔮 Forecast",
    "tab batch"
])
# === Tab 1: Molecule-Level Market Breakdown ===
# === Tab 1A: Executive Summary ===
with tab1a:
    st.subheader("🧬 Executive Summary")

    summary = generate_exec_summary_data(df, selected_combo)

    # Block 1: Sales & Growth
    st.markdown("### 💰 Sales & Growth")
    col1, col2, col3 = st.columns(3)
    col1.metric("2024 Sales (AED)", f"{summary['total_sales']:,.0f}")
    col2.metric("2024 Units", f"{summary['total_units']:,.0f}")
    col3.metric("Unique Manufacturers", summary['unique_manufacturers'])
    
    col4, col5 = st.columns(2)
    col4.metric("CAGR (Units)", f"{summary['unit_cagr']:.1f}%")
    col5.metric("CAGR (Value)", f"{summary['value_cagr']:.1f}%")
    
    # 👉 New: Predicted Revenue
    st.markdown("#### 📈 Predict Your Entry Revenue")
    entry_pct = st.number_input("🔢 Expected Market Capture (%)", min_value=0.0, max_value=100.0, value=8.0, step=0.5)
    adjusted_cif_price = (summary["total_sales"] / 1.4) * 0.4
    predicted_revenue = adjusted_cif_price * (entry_pct / 100)
    
    st.metric("💡 Predicted Revenue (AED)", f"{predicted_revenue:,.0f}")
    
    st.divider()

        # Block 1: Sales & Growth
    st.markdown("### 💰 2025 Sales & Units")
    col20, col21, col22 = st.columns(3)
    col20.metric("2025 Sales (AED)", f"{summary['total_sales_2025']:,.0f}")
    col21.metric("2025 Units", f"{summary['total_units_2025']:,.0f}")
    col22.metric("📊 Predicted Sales (2x Units)", f"{summary['total_sales_2025'] * 2:,.0f}")


   # Block 2: Market Leaders
    st.markdown("### 🥇 Market Leaders")
    col6, col7 = st.columns(2)
    col6.metric("Top Manufacturer", summary['top_2024_manufacturer'])
    col7.metric("Market Share", f"{summary['top_2024_share']:.1f}%")
    
    st.markdown(f"**Originator Value Share Change:** {summary['originator_share_change']}")
    st.markdown(f"**Top 3 Manufacturers:**")
    for manu, share in summary["top3_manufacturers"].items():
        st.markdown(f"- `{manu}` → {share:.1f}%")
    
    st.markdown(f"**# Manufacturers >3% Share**: `{summary['manufacturers_above_3_pct']}`")
    
    # 👉 New: Top product and launch year
    st.markdown(f"**Top Product (from {summary['top_2024_manufacturer']}):** `{summary['top_product']}`")
    if summary['top_product_launch_year']:
        st.markdown(f"**Launch Year:** `{summary['top_product_launch_year']}`")
    
    st.divider()

    # Block 3: Market Split
    st.markdown("### 🏪 Market Split")
    col8, col9 = st.columns(2)
    col8.metric("Private Market", f"{summary['private_pct']:.1f}%")
    col9.metric("LPO Market", f"{summary['lpo_pct']:.1f}%")

    col10, col11 = st.columns(2)
    col10.metric("Private CAGR (Units)", f"{summary['private_cagr']:.1f}%")
    col11.metric("LPO CAGR (Units)", f"{summary['lpo_cagr']:.1f}%")

    st.divider()

    # Block 4: ATC Classification
    st.markdown("### 🧬 ATC Classification")
    st.markdown(f"""
    - **ATC1**: {summary['atc1']}  
    - **ATC2**: {summary['atc2']}  
    - **ATC3**: {summary['atc3']}  
    - **ATC4**: {summary['atc4']}
    """)

    st.divider()

    # Block 5: 📈 5-Year Forecast
    st.markdown("### 📈 Market Forecast (2025–2029)")

    forecast_table = pd.DataFrame({
        "Year": list(summary["forecast_units"].keys()),
        "Forecasted Units": list(summary["forecast_units"].values()),
        "Forecasted Value (AED)": list(summary["forecast_value"].values())
    })

    st.dataframe(forecast_table, use_container_width=True)

    st.caption("🔮 Based on historical CAGR from 2021–2024. These values are simple forecasts and assume trend continuation.")

    st.divider()

    # Block 6: 🧬 Class Overview
    st.markdown("### 🧬 Class Overview (2024)")

    st.markdown("#### 📦 ATC4 Level")
    st.markdown(f"**ATC4 Name:** {summary['atc4']}")
    colA1, colA2, colA3 = st.columns(3)
    colA1.metric("2024 Value (AED)", f"{summary['atc4_metrics']['value_2024']:,.0f}")
    colA2.metric("CAGR (Value)", f"{summary['atc4_metrics']['value_cagr']:.1f}%")
    colA3.metric("CAGR (Units)", f"{summary['atc4_metrics']['unit_cagr']:.1f}%")

    st.markdown("#### 🧪 ATC3 Level")
    st.markdown(f"**ATC3 Name:** {summary['atc3']}")
    colB1, colB2, colB3 = st.columns(3)
    colB1.metric("2024 Value (AED)", f"{summary['atc3_metrics']['value_2024']:,.0f}")
    colB2.metric("CAGR (Value)", f"{summary['atc3_metrics']['value_cagr']:.1f}%")
    colB3.metric("CAGR (Units)", f"{summary['atc3_metrics']['unit_cagr']:.1f}%")
    

    st.divider()
    
        # Block 4: Regulatory Snapshot
    st.markdown("### 📜 Regulatory Snapshot")

        # --- Load Data ---
    ob_products = pd.read_csv("OBproducts.csv")
    ob_patents  = pd.read_csv("OBpatents.csv")

        # --- Clean Orange Book product data ---
    ob_products.columns = ob_products.columns.str.strip()
    ob_products["Ingredient"] = ob_products["Ingredient"].astype(str).str.upper().str.strip()
    ob_products["Ingredient_List"] = ob_products["Ingredient"].str.split(";")
    ob_products["Ingredient_Formatted"] = ob_products["Ingredient_List"].apply(lambda x: " +".join(x))
    ob_products["Ingredient_Formatted_Clean"] = ob_products["Ingredient_Formatted"].str.strip().str.upper()

    reg_data = get_regulatory_summary(selected_combo, mohap_df, ob_products, ob_patents)

    colA, colB = st.columns(2)
    colA.metric("MOHAP Registered Manufacturers", reg_data["mohap_manufacturers"])
    colB.metric("Orange Book Latest Expiry", str(reg_data["orange_book_expiry"]))

    st.markdown(f"**Search logic**: includes any ingredient that contains the term `{selected_combo.upper()}`.")
    st.divider()
with tab1b:
    st.subheader("🧪 Molecule-Level Market Breakdown")

    plot_market = st.radio(
        "Market Type:",
        ["PRIVATE MARKET", "LPO", "TOTAL (PRIVATE + LPO)"],
        horizontal=True
    )
    plot_metric = st.radio(
        "Metric:",
        ["Units", "Value"],
        horizontal=True
    )
    group_by_column = st.radio(
        "Group By:",
        ["Manufacturer", "Product", "Strength", "NFC3"],  # 🆕 NFC3 added here
        horizontal=True
    )

    use_value         = (plot_metric == "Value")
    use_market_filter = (plot_market != "TOTAL (PRIVATE + LPO)")
    market_type_pass  = plot_market

    # Core plot and summary
    fig_mol, mol_summary = plot_combination_market_breakdown_plotly(
        df,
        selected_molecule=selected_combo,
        use_market_filter=use_market_filter,
        market_type=market_type_pass,
        use_value=use_value,
        group_by_column=group_by_column
    )
    if fig_mol:
        st.plotly_chart(fig_mol, use_container_width=True)
        show_manu_summary = st.toggle("📊 Show 2024 Summary Table")
        if show_manu_summary:
            st.subheader("🔢 2024 Manufacturer Summary")
            st.dataframe(mol_summary)
    else:
        st.warning("⚠️ No molecule-level data to show for that selection.")

    # Optional market share trends
    show_share_plot = st.toggle("📈 Show Market Share Line Chart")
    if show_share_plot:
        share_market_type = "TOTAL" if not use_market_filter else market_type_pass
        fig_share = plot_manufacturer_market_share(
            df,
            selected_molecule=selected_combo,
            market_type=share_market_type
        )
        if fig_share:
            st.plotly_chart(fig_share, use_container_width=True)
        else:
            st.warning("⚠️ Not enough data to show market share trends.")


# === Tab: NFC3 + Strength Growth ===
with tab_nfc3_growth:
    st.subheader("📈 Market Growth Breakdown (NFC3 & Strength)")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### NFC3 Growth Breakdown")
        nfc3_card = generate_growth_by_column_card(df, combo=selected_combo, group_col="NFC3")
        st.markdown(nfc3_card, unsafe_allow_html=True)

    with col2:
        st.markdown("### Strength Growth Breakdown")
        strength_card = generate_growth_by_column_card(df, combo=selected_combo, group_col="Strength")
        st.markdown(strength_card, unsafe_allow_html=True)

# === Tab 2: ATC4 Breakdown ===
with tab2:
    st.subheader("🔍 ATC4 Market Breakdown")

    atc4_name = df.loc[
        df["Molecule Combination"] == selected_combo,
        "ATC4"
    ].dropna().unique()[0]

    fig_atc4, atc4_summary = plotly_combinations_within_atc4_go(
        df,
        atc4_name=atc4_name,
        UseValue=use_value
    )
    if fig_atc4:
        st.plotly_chart(fig_atc4, use_container_width=True)
        # Display Top 5 Winners and Losers
        sort_cagr_col = "Value CAGR (%)" if use_value else "Units CAGR (%)"
        st.markdown("### 🏆 Top 5 Winners by CAGR")
        top_5_winners = atc4_summary.sort_values(by=sort_cagr_col, ascending=False).head(5)
        st.dataframe(top_5_winners[["Combination", sort_cagr_col]])

        st.markdown("### 📉 Top 5 Losers by CAGR")
        top_5_losers = atc4_summary.sort_values(by=sort_cagr_col, ascending=True).head(5)
        st.dataframe(top_5_losers[["Combination", sort_cagr_col]])

    show_atc4_summary = st.toggle("📊 Show Full 2024 ATC4 Summary")
    if show_atc4_summary:
        st.subheader("🔢 2024 ATC4 Summary")
        st.dataframe(atc4_summary)


# === Tab 3: Summary + Packs ===
with tab3:
    st.subheader("📋 Molecule Summary and Pack Overview")

    summary_df = generate_molecule_overview(df, selected_combo)
    if summary_df is not None:
        st.table(summary_df)
    else:
        st.warning(f"❌ No summary data for '{selected_combo}'")

    st.markdown("---")
    packs_md = generate_combination_first_clean_summary(df, selected_combo)
    st.markdown(packs_md)


# === Tab 4: MOHAP Insights ===
with tab4:
    st.subheader("🏛️ MOHAP Registered Product Landscape")

    # Ingredient dropdown
    ingredient_opts = sorted(mohap_df["Ingredient"].dropna().unique())
    choice = st.selectbox("🔎 Search by Ingredient (MOHAP):", [""] + ingredient_opts)
    if choice:
        format_registered_products_by_company(choice, mohap_df)

with tab5:
    st.subheader("📅 Orange Book Patent Expiry Lookup")

    # --- Load Data ---
    ob_products    = pd.read_csv("OBproducts.csv")
    ob_patents     = pd.read_csv("OBpatents.csv")
    ob_exclusive   = pd.read_csv("OBexclusivity.csv")  # ✅ Load this too

    # --- Clean Orange Book product data ---
    ob_products.columns = ob_products.columns.str.strip()
    ob_products["Ingredient"] = ob_products["Ingredient"].astype(str).str.upper().str.strip()
    ob_products["Ingredient_List"] = ob_products["Ingredient"].str.split(";")
    ob_products["Ingredient_Formatted"] = ob_products["Ingredient_List"].apply(lambda x: " +".join(x))
    ob_products["Ingredient_Formatted_Clean"] = ob_products["Ingredient_Formatted"].str.strip().str.upper()

    # --- Dropdown selection ---
    selected_ingredient = st.selectbox(
        "🔎 Select Ingredient Combination:",
        sorted(ob_products["Ingredient_Formatted_Clean"].dropna().unique())
    )

    # --- Display patent + exclusivity summary ---
    display_patent_summary(ob_products, ob_patents, ob_exclusive, selected_ingredient)
with tab6:
    st.subheader("📉 Originator Erosion & Uptake Curve")

    with st.spinner("Analyzing erosion and plotting uptake..."):
        try:
            fig, erosion_summary = plot_market_erosion(df.copy(), selected_combo)

            if fig:
                st.plotly_chart(fig, use_container_width=True)

            if erosion_summary:
                st.markdown(f"""
### 📉 **Originator Erosion for `{selected_combo.upper()}`**
- **2021 Market Share:** {erosion_summary['originator_2021']:.2%}  
- **2024 Market Share:** {erosion_summary['originator_2024']:.2%}  
- **Drop:** {erosion_summary['drop']:.2f}%

---

### 📊 **ATC4 Erosion Benchmark – `{erosion_summary['atc4_code']}`**
- **Average Erosion Across ATC4:** {erosion_summary['average_atc4_erosion']:.2f}%  
- **Avg Originator Share in 2021:** {erosion_summary['avg_originator_2021']:.2%}  
- **Avg Originator Share in 2024:** {erosion_summary['avg_originator_2024']:.2%}
                """)
        except Exception as e:
            st.error(f"An error occurred: {e}")

with tab7:
    st.subheader("🔮 Product-Level Forecast")

    # 1) pick a product under the selected molecule combo
    prods = (
        df[df["Molecule Combination"] == selected_combo]
          ["Product"]
          .str.upper()
          .drop_duplicates()
          .tolist()
    )
    selected_product = st.selectbox("🔎 Select Product:", prods, key="forecast_prod")

    # 2) inputs for penetration & growth
    pen = st.number_input("Market Penetration Y1 (%):", min_value=0.0, max_value=100.0, value=3.0, step=0.5, key="forecast_pen") / 100
    gr  = st.number_input("YoY Growth Rate (%):",       min_value=0.0, max_value=100.0, value=10.0, step=0.5, key="forecast_gr")  / 100

    if st.button("Run Forecast", key="run_forecast"):
        fc = forecast_molecule_product_fmt(df, selected_combo, selected_product, pen, gr)
        st.dataframe(fc, use_container_width=True)


import re

def parse_aed(aed_str):
    """
    Converts 'AED 1.23K' or 'AED 2.5M' → float value in AED.
    """
    if pd.isna(aed_str): return 0
    aed_str = str(aed_str).replace("AED", "").strip()
    match = re.match(r"([0-9.,]+)([KM]?)", aed_str)
    if not match:
        return 0
    val, suffix = match.groups()
    val = float(val.replace(",", ""))
    if suffix == "K":
        val *= 1_000
    elif suffix == "M":
        val *= 1_000_000
    return val

import re

# ─── Revenue Parser ──────────────────────────────────────────────────────────────
def parse_aed(aed_str):
    if pd.isna(aed_str): return 0
    aed_str = str(aed_str).replace("AED", "").strip()
    match = re.match(r"([0-9.,]+)([KM]?)", aed_str)
    if not match: return 0
    val, suffix = match.groups()
    val = float(val.replace(",", ""))
    if suffix == "K": val *= 1_000
    elif suffix == "M": val *= 1_000_000
    return val

# ─── Percentage Formatter ────────────────────────────────────────────────────────
def pct_fmt(x):
    return f"{x:.1f}%" if pd.notna(x) else "N/A"

# === Tab 7: Batch Forecasts ===
with tab_batch:
    st.subheader("🧮 Select one or more Molecule ▶ Product to forecast")

    # Unique Molecule→Product pairs
    pairs = (
        df[["Molecule Combination", "Product"]]
        .drop_duplicates()
        .sort_values(["Molecule Combination", "Product"])
    )

    options = []
    for combo, prod in zip(pairs["Molecule Combination"], pairs["Product"]):
        label = f"{combo} → {prod}"
        if top_product_for_combo.get(combo) == prod:
            label += " ★"
        options.append(label)

    selections = st.multiselect(
        "🔎 Pick Molecule + Product",
        options,
        help="You can Ctrl-click (or Cmd-click) to select multiple."
    )

    if not selections:
        st.info("Select at least one pair above to see your batch forecast.")
    else:
        results = []
        total_y1 = 0
        total_y2 = 0
        total_y3 = 0

        for sel in selections:
            combo, prod = [s.strip() for s in sel.replace("★", "").split("→")]
            try:
                fc = forecast_molecule_product_fmt(df, combo, prod)
                fc.insert(0, "Molecule Combination", combo)

                # === FIXED LPO/Private Split Calculation ===
                mol_df = df[df["Molecule Combination"].str.upper() == combo.upper()].copy()
                mol_df["Market"] = mol_df["Market"].astype(str).str.upper().str.strip()
                mol_df["2024 Units"] = pd.to_numeric(mol_df["2024 Units"], errors="coerce").fillna(0)
                mol_df["n_mols"] = mol_df["Molecule Combination"].str.count(r" \+ ") + 1
                mol_df["2024 Units"] = mol_df["2024 Units"] / mol_df["n_mols"]

                private_units = mol_df[mol_df["Market"] == "PRIVATE MARKET"]["2024 Units"].sum()
                lpo_units     = mol_df[mol_df["Market"] == "LPO"]["2024 Units"].sum()
                total_units   = private_units + lpo_units

                private_pct = (private_units / total_units * 100) if total_units else 0
                lpo_pct     = (lpo_units / total_units * 100) if total_units else 0

                fc["Private %"] = pct_fmt(private_pct)
                fc["LPO %"]     = pct_fmt(lpo_pct)

                results.append(fc)

                # Revenue Totals
                total_y1 += fc["Y1 Revenue"].map(parse_aed).sum()
                total_y2 += fc["Y2 Revenue"].map(parse_aed).sum()
                total_y3 += fc["Y3 Revenue"].map(parse_aed).sum()

            except Exception as e:
                st.error(f"⚠️ Forecast for `{combo}` → `{prod}` failed: {e}")

        if results:
            # Merge results with spacers
            merged = []
            for fc in results:
                merged.append(fc)
                spacer = pd.DataFrame([[None]*len(fc.columns)], columns=fc.columns)
                merged.append(spacer)
            batch_df = pd.concat(merged, ignore_index=True)

            st.dataframe(batch_df, use_container_width=True)

            # Markdown Summary
            summary_md = f"""
            ### 💼 Portfolio Revenue Summary
            **Total Y1 Revenue:** {total_y1:,.0f}  
            **Total Y2 Revenue:** {total_y2:,.0f}  
            **Total Y3 Revenue:** {total_y3:,.0f}
            """
            st.markdown(summary_md)