import os
import sys


def get_base_path():
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


BASE_DIR = get_base_path()

RESOURCES_DIR = os.path.join(BASE_DIR, "resources")
CORE_DIR = os.path.join(BASE_DIR, "core")
CONFIG_DIR = os.path.join(CORE_DIR, "config")
ICONS_DIR = os.path.join(RESOURCES_DIR, "icons")
TEMPLATES_DIR = os.path.join(RESOURCES_DIR, "templates")

FIREWALL_TEMPLATE_PATH = os.path.join(
    TEMPLATES_DIR,
    "firewall_template.xlsx"
)

LOG_DIR = os.path.join(BASE_DIR, "logs")