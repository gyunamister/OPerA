import json


def read_config():
    with open("/Users/gyunam/Documents/DigitalTwin/src/dtwin/infosystem/process/config/config.json") as config_json:
        config = json.loads(config_json.read())
    return config['config']


def update_config(valve, value):
    config = read_config()
    new_config = {'config': config}
    with open("/Users/gyunam/Documents/DigitalTwin/src/dtwin/infosystem/process/config/config.json", 'w') as file:
        new_config['config'][valve] = value
        json.dump(new_config, file, indent=4)
