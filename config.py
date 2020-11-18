import configparser
import os

from logger import get_logger

LOGGER = get_logger(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, 'config.ini')


def load_config():
    if os.path.exists(CONFIG_FILE):
        # This is for local deploy with a config file
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE)
        LOGGER.info("Configuration loaded from config file", extra={'file': CONFIG_FILE})
    else:
        # This is for Heroku where configvars are set as environ variables
        config = {
            "DEFAULT": {
                "Token": os.environ.get("Token"),
                "Guild": os.environ.get("Guild"),
                "Channel": os.environ.get("Channel"),
                "AdminChannel": os.environ.get("AdminChannel"),
                "Role": os.environ.get("Role"),
                "List": os.environ.get("List"),
                "ValidationField": os.environ.get("ValidationField")
            }
        }
        LOGGER.info("Configuration loaded from environment variables")
    return config
