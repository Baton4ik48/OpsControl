import os

def load_styles():
    base_dir = os.path.dirname(__file__)

    files = [
        "base.qss",
        "buttons.qss",
        "sidebar.qss",
        "workspace.qss",
        "table.qss",
        "menu.qss",
        "loader.qss",
        "settings.qss"
    ]

    style = ""
    for name in files:
        path = os.path.join(base_dir, name)
        with open(path, "r", encoding="utf-8") as f:
            style += f.read() + "\n"

    return style
