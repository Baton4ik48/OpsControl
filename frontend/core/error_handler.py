from PyQt6.QtWidgets import QMessageBox
from core.api.base import ApiError


def handle_api_error(parent, error: ApiError):
    code = error.status_code
    message = error.message

    # ---------- AUTH / SECURITY ----------
    if code == 403:
        QMessageBox.critical(
            parent,
            "Доступ запрещён",
            "Неверный пароль администратора"
        )

    # ---------- NOT FOUND ----------
    elif code == 404:
        QMessageBox.warning(
            parent,
            "Не найдено",
            "Запрошенные данные не найдены"
        )

    # ---------- CONFLICT / STATE ----------
    elif code == 409:
        QMessageBox.warning(
            parent,
            "Конфликт",
            message or "Операция недоступна в текущем состоянии"
        )

    # ---------- VAULT / STORAGE ----------
    elif code == 503:
        QMessageBox.critical(
            parent,
            "Хранилище недоступно",
            "Vault временно недоступен.\nПопробуйте позже."
        )

    elif code == 504:
        QMessageBox.warning(
            parent,
            "Таймаут",
            "Превышено время ожидания ответа от сервера"
        )

    # ---------- INTERNAL ----------
    elif code == 500:
        QMessageBox.critical(
            parent,
            "Ошибка сервера",
            "Внутренняя ошибка сервера.\nОбратитесь к администратору."
        )

    # ---------- NETWORK ----------
    elif code is None:
        QMessageBox.critical(
            parent,
            "Соединение",
            "Backend недоступен.\nПроверьте сеть или VPN."
        )

    # ---------- FALLBACK ----------
    else:
        QMessageBox.critical(
            parent,
            "Ошибка",
            message or "Неизвестная ошибка"
        )
