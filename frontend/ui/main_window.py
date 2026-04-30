import os

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QMessageBox, QApplication, QTabWidget
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QTimer

from core.paths import ICONS_DIR
from core.config.user_settings import UserSettings
from core.api import ApiClient
from ui.error_handler import handle_api_error
from core.api.base import ApiError
from ui.managers.busy_manager import BusyManager

from controllers.tree_controller import TreeController

from ui.widgets.tools_menu import ToolsMenu
from ui.widgets.sidebar import Sidebar
from ui.widgets.device_tree import DeviceTree
from ui.widgets.busy_overlay import BusyOverlay
from ui.dialogs.settings_dialog import SettingsDialog
from ui.dialogs.password_rotation_dialog import PasswordRotationDialog
from ui.dialogs.statistics_dialog import StatisticsDialog


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("OpsControl Manager")
        self.setWindowIcon(QIcon(os.path.join(ICONS_DIR, "app_icon.png")))
        self.resize(1200, 700)

        # =========================
        # SETTINGS
        # =========================
        self.user_settings = UserSettings()

        # =========================
        # UI
        # =========================
        main_layout = QVBoxLayout(self)
        body = QHBoxLayout()

        self.menu = ToolsMenu(self.user_settings)
        self.sidebar = Sidebar()
        self.tree = DeviceTree()
        self.tree_xclarity = DeviceTree()
        self.tabs = QTabWidget()
        self.tabs.addTab(self.tree, "Основные серверы")
        self.tabs.addTab(self.tree_xclarity, "xClarity")
        main_layout.setMenuBar(self.menu)

        body.addWidget(self.sidebar)
        body.addWidget(self.tabs)
        main_layout.addLayout(body)

        # =========================
        # BUSY
        # =========================
        self.busy = BusyManager()
        self.busy_overlay = BusyOverlay(self)

        self.busy.started.connect(self.busy_overlay.show_message)
        self.busy.finished.connect(self.busy_overlay.hide_overlay)

        # =========================
        # API + CONTROLLERS
        # =========================
        self.api = ApiClient()
        self.controller = TreeController(
            self.api, self.tree, self.tree_xclarity, self.user_settings, self.busy
        )

        # =========================
        # AUTO REFRESH
        # =========================
        self.auto_refresh_timer = QTimer(self)
        self.auto_refresh_timer.timeout.connect(self.on_refresh_all)
        self._apply_auto_refresh()

        # =========================
        # SIGNALS
        # =========================
        self.menu.infrastructure_closed.connect(self.reload)
        self.menu.statistics_requested.connect(self._open_statistics)
        self.sidebar.reload_clicked.connect(self.reload)
        self.sidebar.refresh_all_clicked.connect(self.on_refresh_all)
        self.sidebar.show_all_clicked.connect(self.on_show_all)
        self.sidebar.show_problem_clicked.connect(self.on_show_problem)
        self.sidebar.settings_clicked.connect(self.open_settings)
        self.sidebar.exit_clicked.connect(self.exit_app)

        self.controller.loaded.connect(self.on_tree_loaded)
        self.controller.error_occurred.connect(self._on_api_error)
        self.controller.checking_started.connect(
            lambda: self.sidebar.set_actions_enabled(False)
        )
        self.controller.checking_finished.connect(
            lambda: self.sidebar.set_actions_enabled(True)
        )
        self.controller.checking_finished.connect(self._update_status_counts)

        for _tree in (self.tree, self.tree_xclarity):
            _tree.refresh_branch_requested.connect(self.controller.refresh_branch)
            _tree.refresh_server_requested.connect(self.controller.refresh_server)
            _tree.refresh_port_requested.connect(self.controller.refresh_port)
            _tree.open_protocol_requested.connect(self.controller.connect_protocol)
            _tree.show_credentials_requested.connect(self.controller.show_credentials)
            _tree.rotate_password_requested.connect(self._open_password_rotation)

        self.tabs.currentChanged.connect(self.controller.set_active_tab)
        self.tabs.currentChanged.connect(self._update_status_counts)

    def _on_api_error(self, error: ApiError):
        handle_api_error(self, error)

    # =========================
    # TREE
    # =========================
    def reload(self):
        self.sidebar.set_actions_enabled(False)
        self.controller.start_load()

    def on_tree_loaded(self):
        self.sidebar.set_actions_enabled(True)

    # =========================
    # ACTIONS
    # =========================
    def on_refresh_all(self):
        self.controller.refresh_all()

    def on_show_all(self):
        self.controller.show_all()

    def on_show_problem(self):
        self.controller.show_problem()

    # =========================
    # AUTO REFRESH
    # =========================
    def _apply_auto_refresh(self):
        self.auto_refresh_timer.stop()

        if self.user_settings.get("auto_refresh_enabled"):
            interval = self.user_settings.get("auto_refresh_interval_sec")
            self.auto_refresh_timer.start(interval * 1000)

    # =========================
    # STATUS COUNTS
    # =========================
    def _update_status_counts(self, _tab_index=None):
        data = self.controller._active_data
        if not data:
            self.menu.update_server_counts(0, 0)
            return
        up = down = 0
        for branch in data:
            for server in branch.get("servers", []):
                ports = server.get("ports", [])
                if not ports:
                    continue
                if any(p.get("is_up") is True for p in ports):
                    up += 1
                else:
                    down += 1
        self.menu.update_server_counts(up, down)

    # =========================
    # STATISTICS
    # =========================
    def _open_statistics(self):
        dlg = StatisticsDialog(self.controller._data, parent=self)
        dlg.exec()

    # =========================
    # PASSWORD ROTATION
    # =========================
    def _open_password_rotation(
        self, server_id: int, ip: str, device_type: str = "linux"
    ):
        if device_type == "windows":
            QMessageBox.information(
                self,
                "Смена пароля — Windows",
                "Автоматическая смена пароля для Windows-серверов не реализована.\n\n"
                "Смените пароль вручную: Управление компьютером → "
                "Локальные пользователи и группы → Пользователи.",
            )
            return

        if device_type == "xclarity":
            QMessageBox.information(
                self,
                "Смена пароля — xClarity",
                "Смена пароля для интерфейсов управления xClarity недоступна.\n\n"
                "Измените пароль через веб-интерфейс xClarity (порт 443).",
            )
            return
        admin_login = self.user_settings.get("admin_login") or ""
        dlg = PasswordRotationDialog(
            server_id, ip, admin_login, device_type=device_type, parent=self
        )
        dlg.exec()

    # =========================
    # SETTINGS
    # =========================
    def open_settings(self):
        old_backend = (
            self.user_settings.get("backend_override_enabled"),
            self.user_settings.get("backend_host"),
            self.user_settings.get("backend_port"),
        )

        dlg = SettingsDialog(self.user_settings, self.api)

        if dlg.exec():
            self._apply_auto_refresh()

            new_backend = (
                self.user_settings.get("backend_override_enabled"),
                self.user_settings.get("backend_host"),
                self.user_settings.get("backend_port"),
            )

            if new_backend != old_backend:
                QMessageBox.information(
                    self,
                    "Требуется перезапуск",
                    "Сетевые изменения вступят в силу после перезапуска приложения.",
                )

    # =========================
    # EXIT
    # =========================
    def exit_app(self):
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Вы уверены, что хотите выйти?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            QApplication.quit()
