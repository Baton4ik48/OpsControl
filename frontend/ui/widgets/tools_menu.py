from PyQt6.QtWidgets import QMenuBar, QMessageBox, QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import pyqtSignal, Qt
from core.api.credentials import CredentialsApi
from core.api.base import ApiError
from ui.dialogs.credentials_dialog import CredentialsDialog
from ui.dialogs.envelope_print_dialog import EnvelopePrintDialog
from ui.dialogs.firewall_dialog import FirewallDialog
from ui.dialogs.infrastructure_dialog import InfrastructureManagerDialog


class _StatusIndicator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 12, 0)
        layout.setSpacing(14)

        self._up = QLabel("● —")
        self._partial = QLabel("● —")
        self._down = QLabel("● —")
        self._up.setStyleSheet(
            "color:#81c995; font-size:9pt; font-weight:bold; background:transparent;"
        )
        self._partial.setStyleSheet(
            "color:#ffd54f; font-size:9pt; font-weight:bold; background:transparent;"
        )
        self._down.setStyleSheet(
            "color:#ef9a9a; font-size:9pt; font-weight:bold; background:transparent;"
        )
        self._up.setMinimumWidth(60)
        self._partial.setMinimumWidth(60)
        self._down.setMinimumWidth(60)
        self._up.setToolTip("Серверов полностью доступно")
        self._partial.setToolTip("Серверов частично доступно")
        self._down.setToolTip("Серверов полностью недоступно")

        layout.addWidget(self._up)
        layout.addWidget(self._partial)
        layout.addWidget(self._down)

    def update_counts(self, up: int, partial: int, down: int):
        self._up.setText(f"● {up}")
        self._partial.setText(f"● {partial}")
        self._down.setText(f"● {down}")


class ToolsMenu(QMenuBar):
    infrastructure_closed = pyqtSignal()
    statistics_requested = pyqtSignal()

    def __init__(self, user_settings, parent=None):
        super().__init__(parent)

        self._settings = user_settings
        self._credentials_api = CredentialsApi()

        # =========================
        # Общее
        # =========================
        general_menu = self.addMenu("Общее")

        stats_action = general_menu.addAction("Статистика")
        stats_action.triggered.connect(self.statistics_requested.emit)

        # =========================
        # Инструменты
        # =========================
        tools_menu = self.addMenu("Инструменты")

        # =========================
        # Индикатор статусов
        # =========================
        self._status = _StatusIndicator()
        self.setCornerWidget(self._status, Qt.Corner.TopRightCorner)

        xfirewall_menu = tools_menu.addMenu("xFirewall")
        firewall_action = xfirewall_menu.addAction("Сгенерировать правила")
        firewall_action.triggered.connect(self.open_firewall_generator)

        tools_menu.addSeparator()

        bd_menu = tools_menu.addMenu("Управление БД")

        infra_action = bd_menu.addAction("Управление инфраструктурой")
        infra_action.triggered.connect(self.open_infrastructure_manager)

        tools_menu.addSeparator()

        envelope_action = tools_menu.addAction("Печать конверта с паролями…")
        envelope_action.triggered.connect(self.open_envelope_print)

    def update_server_counts(self, up: int, partial: int, down: int):
        self._status.update_counts(up, partial, down)

    # -------------------------------------

    def open_firewall_generator(self):
        dlg = FirewallDialog(self)
        dlg.setModal(True)
        dlg.exec()

    # -------------------------------------

    def open_envelope_print(self):
        username = self._settings.get("admin_login") or ""
        dlg = CredentialsDialog(mode="envelope")
        dlg.submitted.connect(lambda pwd: self._open_envelope(username, pwd))
        dlg.exec()

    def _open_envelope(self, username: str, master_password: str):
        dlg = EnvelopePrintDialog(username, master_password, self)
        dlg.exec()

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
                QMessageBox.warning(self, "Доступ запрещён", "Неверный мастер-пароль.")
            elif e.status_code == 429:
                QMessageBox.warning(
                    self,
                    "Слишком много попыток",
                    f"Попробуйте через {e.retry_after} сек.",
                )
            else:
                QMessageBox.critical(self, "Ошибка", e.message)
            return

        dlg = InfrastructureManagerDialog(self)
        dlg.setModal(True)
        dlg.exec()
        self.infrastructure_closed.emit()
