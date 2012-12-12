from collections import defaultdict
import os
import sys

if sys.version_info.major == 2:
    from ConfigParser import SafeConfigParser
else:
    from configparser import SafeConfigParser


config_location = os.path.join(os.path.split(__file__)[0], 'settings.cfg')


def get_config():
    config = SafeConfigParser()
    if os.path.exists(config_location):
        config.read(config_location)

    cfg_dict = defaultdict(lambda: defaultdict(str))
    for section in config.sections():
        cfg_dict[section] = defaultdict(str, config.items(section))

    return cfg_dict

def write_config(cfg_dict):
    config = SafeConfigParser()

    for section in cfg_dict:
        config.add_section(section)
        for (key, value) in cfg_dict[section].items():
            config.set(section, key,value)

    with open(config_location, 'w+') as configfile:
        config.write(configfile)
