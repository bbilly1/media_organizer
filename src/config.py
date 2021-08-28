""" config as separate module to avoid circular import """

import json
import sys

from os import path


def get_config():
    """ read out config file and return config dict """
    # build path
    root_folder = path.dirname(sys.argv[0])
    if root_folder == '/sbin':
        # running interactive
        config_path = 'config.json'
    else:
        config_path = path.join(root_folder, 'config.json')
    # parse
    with open(config_path, 'r', encoding='utf-8') as config_file:
        data = config_file.read()
    config = json.loads(data)
    return config
