import pandas as pd
import streamlit as st

def safe_fmt(val, num_fmt="{:,.2f}", default="N/A"):
    try:
        return num_fmt.format(float(val))
    except (ValueError, TypeError):
        return default

def compute_cagr(start, end, years=4):
    try:
        if start <= 0 or end <= 0:
            return 0
        return ((end / start) ** (1 / years) - 1) * 100
    except:
        return 0

def generate_combination_first_clean_summary(df, molecule_name):
    molecule_name = molecule_name.strip().upper()
    mol_df = df[df["Molecule Combination"].str.upper() == molecule_name].copy()
    if mol_df.empty:
        st.warning(f"No data found for molecule: {molecule_name}")
        return

    for col in ["2021 Units", "2024 Units", "2021 LC Value", "2024 LC Value", "Retail Price"]:
        if col in mol_df.columns:
            mol_df[col] = pd.to_numeric(mol_df[col], errors='coerce').fillna(0)

    mol_df["Pack Value 2024"] = mol_df["Retail Price"] * mol_df["2024 Units"]
    mol_df["Pack Value 2021"] = mol_df["Retail Price"] * mol_df["2021 Units"]

    mono_mask = mol_df["Molecule Combination Type"].str.upper() == "MONO"
    combi_mask = ~mono_mask

    def _agg_cagr(df_, col_21, col_24):
        return compute_cagr(df_[col_21].sum(), df_[col_24].sum())

    mono_units_cagr = _agg_cagr(mol_df[mono_mask], "2021 Units", "2024 Units")
    combi_units_cagr = _agg_cagr(mol_df[combi_mask], "2021 Units", "2024 Units")
    mono_value_cagr = _agg_cagr(mol_df[mono_mask], "2021 LC Value", "2024 LC Value")
    combi_value_cagr = _agg_cagr(mol_df[combi_mask], "2021 LC Value", "2024 LC Value")

    st.markdown(f"## 📦 Product & Pack Breakdown for `{molecule_name}`")
    st.markdown(f"### 📈 Mono vs. Combo CAGR (2021 → 2024)")
    st.markdown(f"- **Mono**: Units CAGR = `{safe_fmt(mono_units_cagr)}%`, Value CAGR = `{safe_fmt(mono_value_cagr)}%`")
    st.markdown(f"- **Combo**: Units CAGR = `{safe_fmt(combi_units_cagr)}%`, Value CAGR = `{safe_fmt(combi_value_cagr)}%`")

    total_units = mol_df["2024 Units"].sum()
    total_value = mol_df["Pack Value 2024"].sum()
    
    for combo, combo_df in mol_df.groupby("Molecule Combination"):
        combo_units = combo_df["2024 Units"].sum()
        combo_value = combo_df["Pack Value 2024"].sum()
        unit_pct = combo_units / (total_units or 1) * 100
        value_pct = combo_value / (total_value or 1) * 100

        units_cagr = compute_cagr(combo_df["2021 Units"].sum(), combo_df["2024 Units"].sum())
        value_cagr = compute_cagr(combo_df["2021 LC Value"].sum(), combo_df["2024 LC Value"].sum())

        st.markdown(f"---\n### 🔗 Combination: `{combo}`")
        st.markdown(f"- 💊 Units Share: `{safe_fmt(unit_pct)}%`, 💰 Value Share: `{safe_fmt(value_pct)}%`")
        st.markdown(f"- 🚀 CAGR: Units = `{safe_fmt(units_cagr)}%`, Value = `{safe_fmt(value_cagr)}%`")
        st.markdown(f"- 🏭 Competitors: `{combo_df['Manufacturer'].nunique()}`")

        for (product, manufacturer, combo_type), prod_df in combo_df.groupby(["Product", "Manufacturer", "Molecule Combination Type"]):
            prod_units = prod_df["2024 Units"].sum()
            prod_value = prod_df["Pack Value 2024"].sum()
            prod_unit_pct = prod_units / (total_units or 1) * 100
            prod_value_pct = prod_value / (total_value or 1) * 100

            st.markdown(f"#### 📌 Product: `{product}` by `{manufacturer}` ({combo_type})")
            st.markdown(f"- 📦 Units: `{safe_fmt(prod_units, '{:,.0f}')}`, 💰 Value: AED `{safe_fmt(prod_value, '{:,.0f}')}`")
            st.markdown(f"- 🌍 Share of Molecule: `{safe_fmt(prod_unit_pct)}%` units, `{safe_fmt(prod_value_pct)}%` value")

            lpo_units = prod_df[prod_df["Market"] == "LPO"]["2024 Units"].sum()
            private_units = prod_df[prod_df["Market"] == "PRIVATE MARKET"]["2024 Units"].sum()
            lpo_pct = lpo_units / (prod_units or 1) * 100
            private_pct = private_units / (prod_units or 1) * 100
            st.markdown(f"- 🏪 Market Split: LPO = `{safe_fmt(lpo_pct)}%`, Private = `{safe_fmt(private_pct)}%`")

            shared_molecules = df[df["Product"] == product]["Molecule"].dropna().unique().tolist()
            shared_molecules = [m for m in shared_molecules if m.upper() != molecule_name]
            shared_note = ", ".join(shared_molecules) if shared_molecules else "Mono-molecule Product"
            st.markdown(f"- 🔄 Shared Molecule(s): {shared_note}")

            total_prod_units = prod_df["2024 Units"].sum()

            for (pack, price, nfc3), pack_df in prod_df.groupby(["Pack", "Retail Price", "NFC3"]):
                pack_units = pack_df["2024 Units"].sum()
                lpo_pack_units = pack_df[pack_df["Market"] == "LPO"]["2024 Units"].sum()
                private_pack_units = pack_df[pack_df["Market"] == "PRIVATE MARKET"]["2024 Units"].sum()
                
                lpo_pack_pct = lpo_pack_units / (pack_units or 1) * 100
                private_pack_pct = private_pack_units / (pack_units or 1) * 100
                within_product_pct = pack_units / (total_prod_units or 1) * 100

                st.markdown(
                    f"• `{pack}` — AED `{safe_fmt(price)}` — {safe_fmt(pack_units, '{:,.0f}')} units "
                    f"(**{safe_fmt(within_product_pct)}% of product**) | "
                    f"LPO: `{safe_fmt(lpo_pack_pct)}%`, Private: `{safe_fmt(private_pack_pct)}%` — {nfc3 or 'NFC3: Unknown'}"
                )