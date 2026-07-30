from PyQt6.QtCore import QThread, pyqtSignal

from core.api.base import ApiError
from core.ssh import ROTATE_FN, SSHRotateError


class BatchRotationWorker(QThread):
    """
    Последовательно меняет пароль на выбранных серверах (только порт 22).

    Порядок для каждого сервера:
      1. Получить текущие учётные данные из Vault (show)
      2. Сменить пароль по SSH
      3. Записать новый пароль в Vault (rotate)

    Если шаг 1 упал с 403 — неверный мастер-пароль, прерываем весь batch.
    Если шаг 2 упал — Vault не трогаем, продолжаем со следующим сервером.
    Если шаг 3 упал — SSH уже сменён: сообщаем об этом отдельно.
    """

    server_done = pyqtSignal(
        int, str, str
    )  # server_id, status("ok"/"error"/"skip"), message
    finished_all = pyqtSignal()

    def __init__(
        self,
        api,
        servers: list,
        master_password: str,
        new_password: str,
        mnemonic: str,
        admin_login: str,
    ):
        super().__init__()
        self._api = api
        self._servers = servers
        self._master_password = master_password
        self._new_password = new_password
        self._mnemonic = mnemonic
        self._admin_login = admin_login
        self._stopped = False

    def stop(self):
        self._stopped = True

    def run(self):
        for server in self._servers:
            if self._stopped:
                break

            server_id = server["id"]
            rotate_fn = ROTATE_FN.get(server.get("device_type", "linux"))

            if not rotate_fn:
                self.server_done.emit(
                    server_id, "skip", "тип устройства не поддерживается"
                )
                continue

            try:
                creds = self._api.show(
                    server_id=server_id,
                    port=22,
                    username=self._admin_login,
                    master_password=self._master_password,
                )
                current_username = creds["username"]
                current_password = creds["password"]
            except ApiError as e:
                if e.status_code == 403:
                    # Неверный мастер-пароль — нет смысла продолжать
                    self.server_done.emit(
                        server_id, "error", "неверный мастер-пароль — batch остановлен"
                    )
                    break
                self.server_done.emit(server_id, "error", f"Vault: {e.message}")
                continue
            except Exception as e:
                self.server_done.emit(server_id, "error", f"Vault: {str(e)}")
                continue

            try:
                rotate_fn(
                    host=server["ip"],
                    username=current_username,
                    current_password=current_password,
                    new_password=self._new_password,
                    port=22,
                )
            except SSHRotateError as e:
                self.server_done.emit(server_id, "error", f"SSH: {str(e)}")
                continue
            except Exception as e:
                self.server_done.emit(server_id, "error", f"SSH: {str(e)}")
                continue

            try:
                self._api.rotate(
                    server_id=server_id,
                    ssh_port=22,
                    new_password=self._new_password,
                    username=self._admin_login,
                    master_password=self._master_password,
                    mnemonic=self._mnemonic,
                )
                self.server_done.emit(server_id, "ok", "")
            except ApiError as e:
                # Критично: SSH сменён, но Vault не обновлён
                self.server_done.emit(
                    server_id,
                    "vault_fail",
                    f"SSH сменён, Vault не обновлён: {e.message}",
                )

        self.finished_all.emit()
