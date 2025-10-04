import pandas as pd
import streamlit as st

def display_patent_summary(products_df, patents_df, exclusivity_df, ingredient_name):
    ingredient_name = ingredient_name.strip().upper()

    # Use the cleaned combination field
    df_match = products_df[
        (products_df["Ingredient_Formatted_Clean"] == ingredient_name) &
        (products_df["Appl_Type"] == "N")
    ].copy()

    if df_match.empty:
        st.warning(f"❌ No NDA (originator) products found for: `{ingredient_name}`")
        return

    # Merge with patents and exclusivity
    merged = pd.merge(df_match, patents_df, how="left", on=["Appl_No", "Product_No"])
    merged = pd.merge(merged, exclusivity_df, how="left", on=["Appl_No", "Product_No"])

    # Convert dates
    merged["Patent_Expire_Date_Text"] = pd.to_datetime(merged["Patent_Expire_Date_Text"], errors="coerce")
    merged["Exclusivity_Expire_Date_Text"] = pd.to_datetime(merged["Exclusivity_Date"], errors="coerce")

    # Sort for display
    merged = merged.sort_values(by=["Appl_No", "Product_No"])

    st.markdown(f"## 🧪 Orange Book NDA Products for: `{ingredient_name}`")
    st.markdown("=" * 60)

    grouped = merged.groupby(["Appl_No", "Product_No", "Trade_Name", "DF;Route", "Applicant", "Strength"])

    all_patent_dates = []
    all_exclusivity_dates = []

    for (appl_no, prod_no, trade_name, route, applicant, strength), group in grouped:
        patent_dates = sorted(group["Patent_Expire_Date_Text"].dropna().unique())
        exclusivity_dates = sorted(group["Exclusivity_Expire_Date_Text"].dropna().unique())

        all_patent_dates.extend(patent_dates)
        all_exclusivity_dates.extend(exclusivity_dates)

        patent_str = ", ".join(d.date().isoformat() for d in patent_dates) if patent_dates else "None"
        exclusivity_str = ", ".join(d.date().isoformat() for d in exclusivity_dates) if exclusivity_dates else "None"

        st.markdown(f"---")
        st.markdown(f"### 💊 Product: `{trade_name}`")
        st.markdown(f"- 📦 **Dosage Form/Route**: `{route}`")
        st.markdown(f"- 🧪 **Strength**: `{strength}`")
        st.markdown(f"- 🏢 **Applicant**: `{applicant}`")
        st.markdown(f"- 🧾 **Appl No / Product No**: `{appl_no} / {prod_no}`")
        st.markdown(f"- 🗓️ **Patent Expiry Dates**: `{patent_str}`")
        st.markdown(f"- 🎖️ **Exclusivity Expiry Dates**: `{exclusivity_str}`")

    # --- Molecule-level Expiry Summary ---
    st.markdown("---")
    st.subheader("📅 Molecule-Level Expiry Summary")

    if all_patent_dates:
        earliest_patent = min(all_patent_dates).date()
        latest_patent = max(all_patent_dates).date()
        st.markdown(f"- 🗓️ **Earliest Patent Expiry**: `{earliest_patent}`")
        st.markdown(f"- 🗓️ **Latest Patent Expiry**: `{latest_patent}`")
    else:
        st.markdown("- 🗓️ **Patent Expiry**: `None`")

    if all_exclusivity_dates:
        earliest_excl = min(all_exclusivity_dates).date()
        latest_excl = max(all_exclusivity_dates).date()
        st.markdown(f"- 🎖️ **Earliest Exclusivity Expiry**: `{earliest_excl}`")
        st.markdown(f"- 🎖️ **Latest Exclusivity Expiry**: `{latest_excl}`")
    else:
        st.markdown("- 🎖️ **Exclusivity Expiry**: `None`")