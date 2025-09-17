from enum import Enum
import builtins

import yaml

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader


def process_key(key: str) -> str:
    """
    Convert human-readable key with spaces to pep8 class name
    :param key: human-readable key from yaml file
    :return:
    """
    new_key = "_".join([i.upper() for i in key.split()])
    return new_key

def process_file(name: str = "config.yaml") -> None:
    """
    Process config file and add yaml to global namespace as ENUMs for local usage
    TODO hard code all of this but its kinda neat for dev
    :param name: File name to be parsed
    :return:
    """
    global config
    stream = open(name, 'r')
    dictionary = yaml.load(stream, Loader)
    for key, value in dictionary.items():
        key = process_key(key)
        match type(value):
            case builtins.dict:
                globals()[key] = Enum(key, value)
                continue
            case _ as value_type:
                config[key] = value

config = dict()

process_file()
if "OTHER_CONFIG_FILES" in config:
    for file in config["OTHER_CONFIG_FILES"]:
        process_file(file)

Config = Enum('Config', config)
