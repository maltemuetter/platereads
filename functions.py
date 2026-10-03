def assign_replicates384(df):
    """
    Assigns replicates in a 384-well plate following a square formation:
    A1 - rep1, A2 - rep2, B1 - rep3, B2 - rep4, and repeats across the plate.

    Parameters:
    df (pd.DataFrame): DataFrame containing 'row' (A-P) and 'column' (1-24) information.

    Returns:
    pd.DataFrame: Updated DataFrame with a new 'replicate' column.
    """
    replicate_map = {(0, 0): 1, (0, 1): 2, (1, 0): 3, (1, 1): 4}

    def get_replicate(row, col):
        return replicate_map[(row % 2, (col + 1) % 2)]

    df["replicate"] = df.apply(
        lambda x: get_replicate(ord(x["row"]) - ord("A"), x["column"]), axis=1
    )
    return df
