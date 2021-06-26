import json


def read_config(directory):
    with open(directory) as config_json:
        config = json.loads(config_json.read())
    return config['config']


def update_config(directory, valve, value):
    config = read_config(directory)
    new_config = {'config': config}
    with open(directory, 'w') as file:
        new_config['config'][valve] = value
        json.dump(new_config, file, indent=4)
