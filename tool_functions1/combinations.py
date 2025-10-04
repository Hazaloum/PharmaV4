import pandas as pd

def create_combination_column(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Ensure columns are clean
    df.columns = df.columns.str.replace("\n", " ", regex=False).str.strip()

    # Normalize molecule column
    df["Molecule"] = df["Molecule"].astype(str).str.strip().str.upper()
    df["Product"] = df["Product"].astype(str).str.strip().str.upper()

    # Step 1: Create a mapping from Product → sorted list of Molecules in that product
    product_molecule_map = (
        df.groupby("Product")["Molecule"]
        .unique()
        .apply(lambda mols: " + ".join(sorted(set(mols))))
        .to_dict()
    )

    # Step 2: Apply combination and type
    df["Molecule Combination"] = df["Product"].map(product_molecule_map)
    df["Molecule Combination Type"] = df["Molecule Combination"].apply(
        lambda x: "MONO" if " + " not in x else "COMBINATION"
    )

    return df
