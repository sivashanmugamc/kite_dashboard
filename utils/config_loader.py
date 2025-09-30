import os
from configparser import ConfigParser

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "config.conf")

def load_config(config_path=CONFIG_PATH):
    parser = ConfigParser()
    parser.read(config_path)
    return parser

# Global config variable for use across the project
config = load_config()
