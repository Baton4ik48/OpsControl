import os
from core.paths import RESOURCES_DIR


def load_styles():
    base_dir = os.path.join(RESOURCES_DIR, "styles")

    files = [
        "base.qss",
        "buttons.qss",
        "sidebar.qss",
        "table.qss",
        "menu.qss",
        "loader.qss",
        "settings.qss",
        "statistics.qss",
    ]

    style = ""
    for name in files:
        path = os.path.join(base_dir, name)
        with open(path, "r", encoding="utf-8") as f:
            style += f.read() + "\n"

    return style
