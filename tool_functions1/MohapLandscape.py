import re
import pandas as pd
import streamlit as st

def clean_ingredient_string(text):
    text = re.sub(r"\(.*?\)", "", str(text))       # drop parentheses
    text = text.replace(",", "").strip().upper()
    return text

def format_registered_products_by_company(molecule_name: str, mohap_df: pd.DataFrame):
    """
    Finds all MOHAP-registered packs for a given ingredient,
    groups them by Company, highlights likely originator,
    and prints expanders with product details + CIF predictions.
    """
    molecule_name_clean = clean_ingredient_string(molecule_name)

    # Normalize columns in‐place
    mohap_df["Ingredient"]       = mohap_df["Ingredient"].astype(str)
    mohap_df["Ingredient_clean"] = mohap_df["Ingredient"].apply(clean_ingredient_string)
    mohap_df["Trade Name"]       = mohap_df["Trade Name"].astype(str).str.strip()
    mohap_df["Form"]             = (
        mohap_df["Form"]
        .astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )
    mohap_df["Strength"]         = mohap_df["Strength"].astype(str).str.strip()
    mohap_df["Company"]          = (
        mohap_df["Company"]
        .astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )
    mohap_df["Agent"]            = (
        mohap_df["Agent"]
        .astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )

    # find matches
    matched = mohap_df[
        mohap_df["Ingredient_clean"].str.contains(molecule_name_clean, na=False)
    ]
    if matched.empty:
        st.warning(f"❌ No registered MOHAP products found for: **{molecule_name}**")
        return

    # convert price & pick originator
    matched["Public Price (AED)"] = pd.to_numeric(
        matched["Public Price (AED)"], errors="coerce"
    )
    company_prices = (
        matched
        .groupby("Company")["Public Price (AED)"]
        .sum()
        .sort_values(ascending=False)
    )
    likely_originator    = company_prices.idxmax()
    originator_price_sum = company_prices.max()

    st.markdown(
        f"🎯 **Likely Originator:** `{likely_originator}`  "
        f"(Total Public Price: **AED {originator_price_sum:,.0f}**)"
    )
    st.markdown("---")

    # prepare subset for listing
    subset = (
        matched[
            [
                "Trade Name",
                "Strength",
                "Form",
                "Company",
                "Source",
                "Agent",
                "Public Price (AED)",
                "Ingredient",
            ]
        ]
        .fillna("Unknown")
        .drop_duplicates()
    )

    # Expanders by company
    st.markdown(f"📦 **Registered MOHAP Products for:** `{molecule_name}`")
    for company, grp in subset.groupby("Company"):
        with st.expander(f"🏭 {company} ({len(grp)} packs)"):
            for _, row in grp.iterrows():
                st.markdown(
                    f"- **{row['Trade Name']}** — {row['Strength']} {row['Form']}  "
                    f"— 💰 AED {row['Public Price (AED)']}  "
                    f"— 🧾 Agent: {row['Agent']}  "
                    f"— 🧪 Ingredient: {row['Ingredient']}"
                )

    # CIF price predictions
    st.markdown("---")
    st.markdown("💰 **Predicted CIF Pricing Based on Originator Packs:**")
    originator_df = subset[subset["Company"] == likely_originator]
    if originator_df.empty:
        st.markdown("❌ No valid originator packs to predict from.")
    else:
        for _, row in originator_df.iterrows():
            public_price = row["Public Price (AED)"]
            cif_price = round((public_price / 1.4) * 0.4, 2)
            st.markdown(
                f"- **{row['Trade Name']}** — {row['Strength']} {row['Form']} → "
                f"Predicted CIF: **AED {cif_price}** (from AED {public_price})"
            )

    # summary
    st.markdown("---")
    st.markdown(
        f"📊 **Summary:** {subset['Trade Name'].nunique()} unique products "
        f"across {subset['Company'].nunique()} manufacturers."
    )

