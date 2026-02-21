import json
import os
from core.paths import RESOURCES_DIR

SETTINGS_FILE = os.path.join(RESOURCES_DIR, "settings.json")

DEFAULT_SETTINGS = {
    "admin_login": "AdminGTM",

    "auto_refresh_enabled": True,
    "auto_refresh_interval_sec": 300,

    "backend_override_enabled": False,
    "backend_scheme": "http",
    "backend_host": "",
    "backend_port": 0,
    "web_ports": [
        {"port": 80, "scheme": "http"},
        {"port": 443, "scheme": "https"}
    ],
    "external_apps": []
}


class UserSettings:
    def __init__(self):
        self._data = DEFAULT_SETTINGS.copy()
        self.load()

    def load(self):
        if not os.path.exists(SETTINGS_FILE):
            self.save()
            return

        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()

                if not content:
                    self.save()
                    return

                data = json.loads(content)
                if isinstance(data, dict):
                    self._data.update(data)

        except Exception:
            self._data = DEFAULT_SETTINGS.copy()
            self.save()

    def save(self):
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2)

    def get(self, key):
        return self._data.get(key)

    def set(self, key, value):
        self._data[key] = value
