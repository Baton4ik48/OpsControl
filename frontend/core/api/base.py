import requests
from core.config import settings
from PyQt6.QtWidgets import QMessageBox


class ApiError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


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

            # HTTP ошибки (403, 404, 500, ...)
            if not r.ok:
                try:
                    detail = r.json().get("detail", r.text)
                except Exception:
                    detail = r.text

                raise ApiError(detail, status_code=r.status_code)

            data = r.json()

        except requests.RequestException as e:
            # проблемы сети / соединения
            raise ApiError(
                "Backend недоступен",
                status_code=None
            ) from e

        # бизнес-ошибка API
        if not data.get("success", False):
            raise ApiError(
                data.get("detail", "Unknown API error"),
                status_code=400
            )

        return data["data"]


    def _handle_api_error(self, e: ApiError):
        code = e.status_code

        if code == 403:
            QMessageBox.critical(
                self,
                "Доступ запрещён",
                "Неверный пароль администратора"
            )

        elif code == 404:
            QMessageBox.warning(
                self,
                "Не найдено",
                "Учётные данные не найдены"
            )

        elif code == 409:
            QMessageBox.warning(
                self,
                "Недоступно",
                "Учётные данные временно недоступны"
            )

        elif code == 503:
            QMessageBox.critical(
                self,
                "Хранилище недоступно",
                "Vault временно недоступен.\nПопробуйте позже."
            )

        elif code == 504:
            QMessageBox.warning(
                self,
                "Таймаут",
                "Превышено время ожидания ответа"
            )

        elif code == 500:
            QMessageBox.critical(
                self,
                "Ошибка сервера",
                "Внутренняя ошибка сервера"
            )

        else:
            QMessageBox.critical(
                self,
                "Ошибка",
                e.message
            )
