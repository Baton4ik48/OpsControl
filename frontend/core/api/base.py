import requests
from core.config import settings

class ApiError(Exception):
    pass

class BaseApi:
    def __init__(self):
        self.base_url = settings.BACKEND_BASE_URL
        self.session = requests.Session()

    def get(self, path: str):
        return self._request("GET", path)

    def put(self, path: str, params=None, json=None):
        return self._request("PUT", path, params=params, json=json)

    def post(self, path: str, params=None, json=None):
        return self._request("POST", path, params=params, json=json)

    def _request(self, method: str, path: str, **kwargs):
        url = f"{self.base_url}{path}"

        try:
            r = self.session.request(method, url, timeout=(3, 30), **kwargs)
            r.raise_for_status()
            data = r.json()
        except requests.RequestException as e:
            raise ApiError(f"Backend error: {e}")

        if not data.get("success", False):
            raise ApiError(data.get("detail", "Unknown API error"))

        return data["data"]

