import pandas as pd
import re
from datetime import date

def clean_ingredient_string(text):
    text = re.sub(r"\(.*?\)", "", str(text))  # Remove parentheses
    text = text.replace(",", "").strip().upper()
    return text

def get_regulatory_summary(molecule_name, mohap_df, ob_products, ob_patents):
    molecule_name_clean = clean_ingredient_string(molecule_name)

    # --- MOHAP Manufacturer Count ---
    mohap_df = mohap_df.copy()
    mohap_df["Ingredient_clean"] = mohap_df["Ingredient"].astype(str).apply(clean_ingredient_string)
    mohap_df["Company"] = mohap_df["Company"].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()

    matched_mohap = mohap_df[mohap_df["Ingredient_clean"].str.contains(molecule_name_clean, na=False)]
    n_mohap_manufacturers = matched_mohap["Company"].nunique()

    # --- Orange Book Expiry Lookup ---
    ob_products = ob_products.copy()
    ob_patents = ob_patents.copy()

    ob_products["Ingredient"] = ob_products["Ingredient"].astype(str).str.upper().str.strip()
    ob_products["Ingredient_List"] = ob_products["Ingredient"].str.split(";")
    ob_products["Ingredient_Formatted"] = ob_products["Ingredient_List"].apply(lambda x: " +".join(x))
    ob_products["Ingredient_Formatted_Clean"] = ob_products["Ingredient_Formatted"].str.strip().str.upper()

    ob_match = ob_products[ob_products["Ingredient_Formatted_Clean"].str.contains(molecule_name_clean, na=False)]
    ob_match = ob_match[ob_match["Appl_Type"] == "N"]  # Only NDA products

    latest_expiry = None
    if not ob_match.empty:
        merged = pd.merge(ob_match, ob_patents, how="left", on=["Appl_No", "Product_No"])
        merged["Patent_Expire_Date_Text"] = pd.to_datetime(merged["Patent_Expire_Date_Text"], errors='coerce')
        expiry_dates = merged["Patent_Expire_Date_Text"].dropna()
        if not expiry_dates.empty:
            latest_expiry = expiry_dates.max().date()

    return {
        "mohap_manufacturers": n_mohap_manufacturers,
        "orange_book_expiry": latest_expiry if latest_expiry else "N/A"
    }