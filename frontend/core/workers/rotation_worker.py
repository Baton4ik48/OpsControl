from PyQt6.QtCore import QThread, pyqtSignal

from core.ssh import ROTATE_FN, rotate_linux_password
from core.utils.secure import wipe


class RotationWorker(QThread):
    """
    Полный цикл смены пароля одного сервера в фоновом потоке:

      1. verify — получить текущие креды из Vault (заодно проверяет мастер-пароль)
      2. ssh    — сменить пароль на устройстве по SSH
      3. vault  — записать новый пароль в Vault

    vault_only=True пропускает шаги 1–2 — режим повторной записи,
    когда SSH уже выполнен, но Vault ранее не ответил.

    error эмитится с именем шага ("verify" / "ssh" / "vault"), чтобы UI
    мог показать сообщение, соответствующее реальному состоянию сервера.
    """

    step_changed = pyqtSignal(str)
    success = pyqtSignal()
    error = pyqtSignal(str, object)  # stage, exception

    def __init__(
        self,
        api,
        server_id: int,
        host: str,
        admin_login: str,
        master_password: str,
        new_password: str,
        mnemonic: str = "",
        device_type: str = "linux",
        vault_only: bool = False,
        ssh_port: int = 22,
    ):
        super().__init__()
        self._api = api
        self._server_id = server_id
        self._host = host
        self._admin_login = admin_login
        self._master_password = master_password
        self._new_password = new_password
        self._mnemonic = mnemonic
        self._device_type = device_type
        self._vault_only = vault_only
        self._ssh_port = ssh_port

    def run(self):
        current_password = None
        try:
            if not self._vault_only:
                self.step_changed.emit("Проверка доступа...")
                try:
                    creds = self._api.show(
                        server_id=self._server_id,
                        port=self._ssh_port,
                        username=self._admin_login,
                        master_password=self._master_password,
                    )
                except Exception as e:
                    self.error.emit("verify", e)
                    return

                current_username = creds["username"]
                current_password = creds["password"]

                self.step_changed.emit("Меняю пароль по SSH...")
                rotate_fn = ROTATE_FN.get(self._device_type, rotate_linux_password)
                try:
                    rotate_fn(
                        host=self._host,
                        username=current_username,
                        current_password=current_password,
                        new_password=self._new_password,
                        port=self._ssh_port,
                    )
                except Exception as e:
                    self.error.emit("ssh", e)
                    return

            self.step_changed.emit("Сохраняю в хранилище...")
            try:
                self._api.rotate(
                    server_id=self._server_id,
                    ssh_port=self._ssh_port,
                    new_password=self._new_password,
                    username=self._admin_login,
                    master_password=self._master_password,
                    mnemonic=self._mnemonic,
                )
            except Exception as e:
                self.error.emit("vault", e)
                return

            self.success.emit()

        finally:
            wipe(self._master_password)
            if current_password is not None:
                wipe(current_password)
            self._master_password = ""
