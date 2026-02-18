import os

FRONTEND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

RESOURCES_DIR = os.path.join(FRONTEND_DIR, "resources")
ICONS_DIR = os.path.join(RESOURCES_DIR, "icons")
TEMPLATES_DIR = os.path.join(RESOURCES_DIR, "templates")

FIREWALL_TEMPLATE_PATH = os.path.join(
    TEMPLATES_DIR,
    "firewall_template.xlsx"
)
