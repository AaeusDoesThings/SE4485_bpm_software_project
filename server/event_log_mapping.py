import pandas as pd


def normalize_case_id_column(df: pd.DataFrame) -> pd.DataFrame:
    if "Case_ID" not in df.columns and "Case_Id" in df.columns:
        return df.rename(columns={"Case_Id": "Case_ID"})
    return df
