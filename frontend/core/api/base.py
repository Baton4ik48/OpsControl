import requests
from core.config import settings
from core.logger import get_logger

log = get_logger(__name__)


class ApiError(Exception):
    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        error_code: str | None = None,
        retry_after: int | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.retry_after = retry_after


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
            r = self.session.request(
                method,
                url,
                timeout=(3, 30),
                **kwargs
            )

            if not r.ok:
                try:
                    payload = r.json()
                except Exception:
                    payload = {}

                raise ApiError(
                    message=payload.get("detail", r.text),
                    status_code=r.status_code,
                    error_code=payload.get("error_code"),
                    retry_after=payload.get("retry_after"),
                )

            data = r.json()

        except requests.RequestException:
            raise ApiError(
                "Backend недоступен",
                status_code=None
            )

        if not data.get("success", False):
            raise ApiError(
                data.get("detail", "Unknown API error"),
                status_code=400
            )

        return data["data"]

