from PyQt6.QtWidgets import QMessageBox
from core.api.base import ApiError
from core.logger import get_logger

log = get_logger(__name__)


def handle_api_error(parent, error: ApiError):
    code = error.status_code

    # THROTTLED
    if code == 429 and error.error_code == "LOGIN_THROTTLED":
        minutes = max(1, (error.retry_after or 60) // 60)

        QMessageBox.warning(
            parent,
            "Слишком много попыток",
            f"Слишком много попыток входа.\n" f"Повторите через {minutes} мин.",
        )
        return

    # INVALID PASSWORD
    if code == 403 and error.error_code == "INVALID_MASTER_PASSWORD":
        QMessageBox.critical(
            parent, "Доступ запрещён", "Неверный пароль администратора"
        )
        return

    # ---------- ОСТАЛЬНОЕ ----------
    if code == 404:
        QMessageBox.warning(parent, "Не найдено", "Запрошенные данные не найдены")

    elif code == 503:
        QMessageBox.critical(
            parent,
            "Хранилище недоступно",
            "Vault временно недоступен.\nПопробуйте позже.",
        )

    elif code == 504:
        QMessageBox.warning(
            parent, "Таймаут", "Превышено время ожидания ответа от сервера"
        )

    elif code == 500:
        QMessageBox.critical(
            parent,
            "Ошибка сервера",
            "Внутренняя ошибка сервера.\nОбратитесь к администратору.",
        )

    elif code is None:
        QMessageBox.critical(
            parent, "Соединение", "Сервер недоступен.\nПроверьте сеть."
        )

    else:
        QMessageBox.critical(parent, "Ошибка", error.message or "Неизвестная ошибка")


def handle_system_error(parent, error: Exception):
    log.exception("System error occurred", exc_info=error)

    if isinstance(error, FileNotFoundError):
        QMessageBox.critical(
            parent,
            "Утилита не найдена",
            "Не найдена системная SSH-утилита.\n\n"
            "Windows: установите PuTTY или KiTTY и добавьте в PATH.\n"
            "Linux: установите пакет sshpass.",
        )
        return

    if isinstance(error, RuntimeError):

        message_map = {
            "PUTTY_NOT_FOUND": "Не найден PuTTY или KiTTY.\nУстановите PuTTY (или KiTTY) и добавьте в PATH.",
            "SSHPASS_NOT_FOUND": "Не найден sshpass.\nУстановите пакет sshpass.",
            "RDP_ONLY_WINDOWS": "RDP доступен только на Windows.",
            "UNSUPPORTED_PROTOCOL": "Данный протокол не поддерживается.",
        }

        QMessageBox.critical(
            parent,
            "Ошибка протокола",
            message_map.get(str(error), "Неизвестная ошибка протокола."),
        )
        return

    QMessageBox.critical(
        parent, "Ошибка приложения", "Произошла непредвиденная ошибка."
    )
