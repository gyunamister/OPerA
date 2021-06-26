from dtween.available.constants import TRANSITION, GUARD
import pandas as pd
from collections import OrderedDict


def guards_to_df(guards) -> pd.DataFrame:
    return pd.DataFrame({TRANSITION: guards.keys(), GUARD: guards.values()})


def df_to_gaurds(df) -> OrderedDict:
    guards = OrderedDict()
    for row in df.iterrows():
        tr_name = row.TRANSITION
        guard = row.GUARD
        guards.update({tr_name: guard})
    return guards
