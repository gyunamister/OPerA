import pandas as pd


def apply(all_df, return_obj_dataframe=False, parameters=None):
    if parameters is None:
        parameters = {}

    eve_cols = [x for x in all_df.columns if not x.startswith("object_")]
    obj_cols = [x for x in all_df.columns if x.startswith("object_")]
    df = all_df[eve_cols]
    obj_df = pd.DataFrame()
    if obj_cols:
        obj_df = all_df[obj_cols]
    df["event_timestamp"] = pd.to_datetime(df["event_timestamp"])
    if "event_start_timestamp" in df.columns:
        df["event_start_timestamp"] = pd.to_datetime(
            df["event_start_timestamp"])
    df = df.dropna(subset=["event_id"])
    df["event_id"] = df["event_id"].astype(str)
    df.type = "succint"

    if return_obj_dataframe:
        obj_df = obj_df.dropna(subset=["object_id"])
        return df, obj_df

    return df
