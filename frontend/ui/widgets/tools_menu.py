from PyQt6.QtWidgets import QMenuBar, QMessageBox
from core.api.credentials import CredentialsApi
from core.api.base import ApiError
from ui.dialogs.credentials_dialog import CredentialsDialog
from ui.dialogs.firewall_dialog import FirewallDialog
from ui.dialogs.infrastructure_dialog import InfrastructureManagerDialog


class ToolsMenu(QMenuBar):
    def __init__(self, user_settings, parent=None):
        super().__init__(parent)

        self._settings = user_settings
        self._credentials_api = CredentialsApi()

        tools_menu = self.addMenu("Инструменты")

        # =========================
        # xFirewall
        # =========================
        xfirewall_menu = tools_menu.addMenu("xFirewall")

        firewall_action = xfirewall_menu.addAction("Сгенерировать правила")
        firewall_action.triggered.connect(self.open_firewall_generator)

        # =========================
        # Infrastructure Manager
        # =========================
        tools_menu.addSeparator()

        bd_menu = tools_menu.addMenu("Управление БД")

        infra_action = bd_menu.addAction("Управление инфраструктурой")
        infra_action.triggered.connect(self.open_infrastructure_manager)

        package_action = bd_menu.addAction("Пакетная загрузка в БД")

    # -------------------------------------

    def open_firewall_generator(self):
        dlg = FirewallDialog(self)
        dlg.setModal(True)
        dlg.exec()

    # -------------------------------------

    def open_infrastructure_manager(self):
        dlg = CredentialsDialog(mode="infra")
        dlg.submitted.connect(self._verify_and_open)
        dlg.exec()

    def _verify_and_open(self, master_password: str):
        username = self._settings.get("admin_login") or ""

        try:
            self._credentials_api.verify_admin(username, master_password)
        except ApiError as e:
            if e.status_code == 403:
                QMessageBox.warning(
                    self,
                    "Доступ запрещён",
                    "Неверный мастер-пароль."
                )
            elif e.status_code == 429:
                QMessageBox.warning(
                    self,
                    "Слишком много попыток",
                    f"Попробуйте через {e.retry_after} сек."
                )
            else:
                QMessageBox.critical(self, "Ошибка", e.message)
            return

        dlg = InfrastructureManagerDialog(self)
        dlg.setModal(True)
        dlg.exec()
