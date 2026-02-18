import os

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QMessageBox, QApplication
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QTimer

from core.paths import ICONS_DIR
from core.config import settings
from core.user_settings import UserSettings
from core.api import ApiClient
from core.api.base import ApiError
from core.error_handler import handle_api_error

from controllers.tree_controller import TreeController
from controllers.console_controller import ConsoleController

from ui.widgets.tools_menu import ToolsMenu
from ui.widgets.sidebar import Sidebar
from ui.widgets.device_tree import DeviceTree
from ui.widgets.console import Console
from ui.widgets.workspace import Workspace
from ui.dialogs.settings_dialog import SettingsDialog


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("PortPass Manager")
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

        self.menu = ToolsMenu()
        self.sidebar = Sidebar()
        self.tree = DeviceTree()
        self.console = Console()
        main_layout.setMenuBar(self.menu)

        workspace = Workspace(self.tree, self.console)

        body.addWidget(self.sidebar)
        body.addWidget(workspace)
        main_layout.addLayout(body)

        # =========================
        # API + CONTROLLERS
        # =========================
        self.api = ApiClient()
        self.controller = TreeController(self.api, self.tree, self.user_settings)

        self.console_controller = ConsoleController(self.console.log)
        self.console.set_handler(self.console_controller.handle)

        # =========================
        # AUTO REFRESH
        # =========================
        self.auto_refresh_timer = QTimer(self)
        self.auto_refresh_timer.timeout.connect(self.on_refresh_all)
        self._apply_auto_refresh()

        # =========================
        # SIGNALS
        # =========================
        self.sidebar.reload_clicked.connect(self.reload)
        self.sidebar.refresh_all_clicked.connect(self.on_refresh_all)
        self.sidebar.show_all_clicked.connect(self.on_show_all)
        self.sidebar.show_problem_clicked.connect(self.on_show_problem)
        self.sidebar.settings_clicked.connect(self.open_settings)
        self.sidebar.exit_clicked.connect(self.exit_app)

        self.controller.loaded.connect(self.on_tree_loaded)
        self.controller.load_failed.connect(self.on_tree_load_failed)

        self.tree.refresh_server_requested.connect(self.controller.refresh_server)
        self.tree.refresh_port_requested.connect(self.controller.refresh_port)

        self.tree.open_ssh_requested.connect(self.controller.open_ssh_terminal)

        self.tree.show_credentials_requested.connect(self.controller.show_credentials)

    # =========================
    # TREE
    # =========================
    def reload(self):
        self.console.log("Загрузка данных…")
        self.sidebar.set_actions_enabled(False)
        self.controller.start_load()

    def on_tree_loaded(self):
        self.sidebar.set_actions_enabled(True)
        self.console.log("Данные загружены")

    def on_tree_load_failed(self, error: ApiError):
        self.sidebar.set_actions_enabled(False)
        self.console.log("Ошибка загрузки данных")

        handle_api_error(self, error)

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
    # SETTINGS
    # =========================
    def open_settings(self):
        dlg = SettingsDialog(self.user_settings)

        if dlg.exec():
            dlg.apply()
            self._apply_auto_refresh()

            if self.user_settings.get("backend_override_enabled"):
                QMessageBox.information(
                    self,
                    "Требуется перезапуск",
                    "Сетевые изменения вступят в силу после перезапуска приложения."
                )

    # =========================
    # EXIT
    # =========================
    def exit_app(self):
        QApplication.quit()