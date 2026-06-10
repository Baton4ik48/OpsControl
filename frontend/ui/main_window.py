import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QMessageBox, QApplication,
    QTabWidget, QStackedWidget, QPushButton, QLabel,
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QTimer

from core.paths import ICONS_DIR
from core.config.user_settings import UserSettings
from core.api import ApiClient
from core.configuration import settings as app_settings
from ui.error_handler import handle_api_error
from core.api.base import ApiError
from ui.managers.busy_manager import BusyManager

from controllers.tree_controller import TreeController

from ui.widgets.tools_menu import ToolsMenu
from ui.widgets.sidebar import Sidebar
from ui.widgets.device_tree import DeviceTree
from ui.widgets.dashboard_view import DashboardView
from ui.widgets.busy_overlay import BusyOverlay
from ui.dialogs.settings_dialog import SettingsDialog
from ui.dialogs.password_rotation_dialog import PasswordRotationDialog
from ui.dialogs.statistics_dialog import StatisticsDialog
from ui.dialogs.batch_rotation_dialog import BatchRotationDialog


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("OpsControl Manager")
        self.setWindowIcon(QIcon(os.path.join(ICONS_DIR, "app_icon.png")))
        self.resize(1200, 700)

        self.user_settings = UserSettings()

        main_layout = QVBoxLayout(self)
        body = QHBoxLayout()

        self.menu = ToolsMenu(self.user_settings)
        self.sidebar = Sidebar()
        main_layout.setMenuBar(self.menu)

        # Основной стек: [0] дашборд-вкладки, [1] детальный вид филиала
        self.content_stack = QStackedWidget()

        # --- Страница 0: вкладки с дашбордами ---
        self.dash_tabs = QTabWidget()
        self.dash_main = DashboardView()
        self.dash_xclarity = DashboardView()
        self.dash_ups = DashboardView()
        self.dash_tabs.addTab(self.dash_main, "Сетевое оборудование")
        self.dash_tabs.addTab(self.dash_xclarity, "BMC")
        self.dash_tabs.addTab(self.dash_ups, "ИБП")

        # --- Страница 1: детальный вид (дерево одного филиала) ---
        self.detail_widget = QWidget()
        detail_layout = QVBoxLayout(self.detail_widget)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(0)

        detail_header = QHBoxLayout()
        detail_header.setContentsMargins(8, 6, 8, 4)
        self.btn_back = QPushButton("← Назад")
        self.btn_back.setFixedWidth(100)
        self.lbl_branch = QLabel()
        self.lbl_branch.setStyleSheet(
            "font-weight: bold; font-size: 11pt; color: #cfd8dc; background: transparent;"
        )
        detail_header.addWidget(self.btn_back)
        detail_header.addSpacing(12)
        detail_header.addWidget(self.lbl_branch)
        detail_header.addStretch()
        detail_layout.addLayout(detail_header)

        self.detail_tree = DeviceTree()
        detail_layout.addWidget(self.detail_tree)

        self.content_stack.addWidget(self.dash_tabs)      # index 0
        self.content_stack.addWidget(self.detail_widget)  # index 1

        body.addWidget(self.sidebar)
        body.addWidget(self.content_stack)
        main_layout.addLayout(body)

        self.busy = BusyManager()
        self.busy_overlay = BusyOverlay(self)
        self.busy.started.connect(self.busy_overlay.show_message)
        self.busy.finished.connect(self.busy_overlay.hide_overlay)

        self.api = ApiClient()
        self.controller = TreeController(
            self.api,
            self.dash_main, self.dash_xclarity, self.dash_ups,
            self.detail_tree,
            self.user_settings, self.busy,
        )

        self.auto_refresh_timer = QTimer(self)
        self.auto_refresh_timer.timeout.connect(self.on_refresh_all)
        self._apply_auto_refresh()

        self.menu.infrastructure_closed.connect(self.reload)
        self.menu.statistics_requested.connect(self._open_statistics)
        self.menu.batch_rotation_requested.connect(self._open_batch_rotation)
        self.sidebar.reload_clicked.connect(self.reload)
        self.sidebar.refresh_all_clicked.connect(self.on_refresh_all)
        self.sidebar.show_all_clicked.connect(self.on_show_all)
        self.sidebar.show_problem_clicked.connect(self.on_show_problem)
        self.sidebar.settings_clicked.connect(self.open_settings)
        self.sidebar.exit_clicked.connect(self.exit_app)

        self.controller.loaded.connect(self.on_tree_loaded)
        self.controller.loaded.connect(self._update_status_counts)
        self.controller.error_occurred.connect(self._on_api_error)
        self.controller.checking_started.connect(
            lambda: self.sidebar.set_actions_enabled(False)
        )
        self.controller.checking_finished.connect(
            lambda: self.sidebar.set_actions_enabled(True)
        )
        self.controller.checking_finished.connect(self._update_status_counts)

        # Двойной клик по карточке → детальный вид
        self.dash_main.branch_selected.connect(self._on_branch_selected)
        self.dash_xclarity.branch_selected.connect(self._on_branch_selected)
        self.dash_ups.branch_selected.connect(self._on_branch_selected)

        # Сигналы дерева в детальном виде
        self.detail_tree.refresh_branch_requested.connect(self.controller.refresh_branch)
        self.detail_tree.refresh_server_requested.connect(self.controller.refresh_server)
        self.detail_tree.refresh_port_requested.connect(self.controller.refresh_port)
        self.detail_tree.open_protocol_requested.connect(self.controller.connect_protocol)
        self.detail_tree.show_credentials_requested.connect(self.controller.show_credentials)
        self.detail_tree.rotate_password_requested.connect(self._open_password_rotation)
        self.detail_tree.comment_changed.connect(self.controller.save_comment)

        self.btn_back.clicked.connect(self._on_back)

        self.dash_tabs.currentChanged.connect(self.controller.set_active_tab)
        self.dash_tabs.currentChanged.connect(self._update_status_counts)

        QTimer.singleShot(0, self._warn_if_insecure)

    def _on_branch_selected(self, branch_name: str):
        self.lbl_branch.setText(branch_name)
        self.controller.drill_into_branch(branch_name)
        self.content_stack.setCurrentIndex(1)

    def _on_back(self):
        self.content_stack.setCurrentIndex(0)
        self.controller.clear_current_branch()

    def _warn_if_insecure(self):
        if app_settings.BACKEND_BASE_URL.startswith("http://"):
            QMessageBox.warning(
                self,
                "Незащищённое соединение",
                f"Подключение к серверу выполняется по протоколу HTTP:\n"
                f"{app_settings.BACKEND_BASE_URL}\n\n"
                "Данные передаются без шифрования.\n"
                "Для защиты трафика настройте HTTPS в разделе «Настройки → Сервер».",
            )

    def _on_api_error(self, error: ApiError):
        handle_api_error(self, error)

    def reload(self):
        self.sidebar.set_actions_enabled(False)
        self.content_stack.setCurrentIndex(0)
        self.controller.start_load()

    def on_tree_loaded(self):
        self.sidebar.set_actions_enabled(True)

    def on_refresh_all(self):
        self.controller.refresh_all()

    def on_show_all(self):
        self.controller.show_all()

    def on_show_problem(self):
        self.controller.show_problem()

    def _apply_auto_refresh(self):
        self.auto_refresh_timer.stop()
        if self.user_settings.get("auto_refresh_enabled"):
            interval = self.user_settings.get("auto_refresh_interval_sec")
            self.auto_refresh_timer.start(interval * 1000)

    def _update_status_counts(self, _tab_index=None):
        data = self.controller._active_data
        if not data:
            self.menu.update_server_counts(0, 0, 0)
            return
        up = partial = down = 0
        for branch in data:
            for server in branch.get("servers", []):
                ports = server.get("ports", [])
                if not ports:
                    continue
                checked = [p for p in ports if p.get("is_up") is not None]
                if not checked:
                    continue
                has_up = any(p["is_up"] is True for p in checked)
                has_down = any(p["is_up"] is False for p in checked)
                if has_up and has_down:
                    partial += 1
                elif has_up:
                    up += 1
                else:
                    down += 1
        self.menu.update_server_counts(up, partial, down)

    def _open_batch_rotation(self):
        data = self.controller._data
        if not data:
            QMessageBox.information(self, "Нет данных", "Сначала загрузите топологию сети.")
            return
        dlg = BatchRotationDialog(data, parent=self)
        dlg.exec()

    def _open_statistics(self):
        dlg = StatisticsDialog(self.controller._data, parent=self)
        dlg.exec()

    def _open_password_rotation(self, server_id: int, ip: str, device_type: str = "linux"):
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
