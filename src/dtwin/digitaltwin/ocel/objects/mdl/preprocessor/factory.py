

def filter_by_timestamp(df, start_timestamp=None, end_timestamp=None):
    if start_timestamp is not None:
        df = df.loc[df["event_timestamp"] >= start_timestamp]
    if end_timestamp is not None:
        df = df.loc[df["event_timestamp"] <= end_timestamp]
    return df


def object_filter_by_timestamp(df, start_timestamp=None, end_timestamp=None, object_type=None):
    if end_timestamp is not None:
        remove_end_df = df.loc[df["event_timestamp"]
                               <= end_timestamp]
    else:
        remove_end_df = df
    if start_timestamp is not None:
        remove_end_start_df = remove_end_df.loc[remove_end_df["event_timestamp"]
                                                >= start_timestamp]
    else:
        remove_end_start_df = remove_end_df

    print(remove_end_start_df)
    object_ids = set(remove_end_start_df[object_type])
    object_ids = [x for x in object_ids if str(x) != 'nan']
    final_df = remove_end_df.loc[remove_end_df[object_type].isin(object_ids)]
    return final_df


def filter_object_df_by_object_ids(df, ids):
    df = df.loc[df["object_id"].isin(ids)]
    return df
