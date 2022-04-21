from dtween.available.constants import TRANSITION, GUARD, ACTIVITY_VARIANTS, VALVES
import pandas as pd
from collections import OrderedDict
import json


def guards_to_df(guards) -> pd.DataFrame:
    return pd.DataFrame({TRANSITION: guards.keys(), GUARD: guards.values()})


def guard_df_to_dict(df) -> OrderedDict:
    guards = OrderedDict()
    for row in df.iterrows():
        tr_name = row.TRANSITION
        guard = row.GUARD
        guards.update({tr_name: guard})
    return guards


def read_config(directory):
    with open(directory) as config_json:
        config = json.loads(config_json.read())
    return config[VALVES], config[ACTIVITY_VARIANTS]


def update_config(directory, valve, value):
    config = read_config(directory)
    new_config = {'config': config}
    with open(directory, 'w') as file:
        new_config['config'][valve] = value
        json.dump(new_config, file, indent=4)
