import os
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QCheckBox, QSpinBox, QLabel, QPushButton,
    QMessageBox, QFileDialog, QLineEdit,
    QGroupBox, QTabWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from controllers.settings_controller import SettingsController
from core.paths import ICONS_DIR


class SettingsDialog(QDialog):
    def __init__(self, settings, api):
        super().__init__()

        self.settings = settings

        self.setWindowIcon(QIcon(os.path.join(ICONS_DIR, "settings_icon.png")))
        self.setWindowTitle("Настройки")

        main_layout = QVBoxLayout(self)

        # =========================
        # STATUS (всегда сверху)
        # =========================
        status_layout = QHBoxLayout()

        self.status_icon = QLabel()
        self.status_icon.setFixedSize(16, 16)
        self.status_text = QLabel("")

        status_layout.addStretch()
        status_layout.addWidget(self.status_icon)
        status_layout.addWidget(self.status_text)
        status_layout.addStretch()

        main_layout.addLayout(status_layout)

        # =========================
        # TABS
        # =========================
        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        main_layout.addWidget(tabs)
        tabs.tabBar().setExpanding(True)
        tabs.tabBar().setUsesScrollButtons(False)   

        # =====================================================
        # TAB 1 — ОБЩИЕ
        # =====================================================
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)

        # --- Авторизация ---
        desc_general = QLabel(
        "Основные параметры работы приложения.\n"
        "Логин администратора и поведение автообновления.")
        desc_general.setWordWrap(True)
        desc_general.setObjectName("settingsDescription")
        desc_general.setAlignment(Qt.AlignmentFlag.AlignCenter)
        general_layout.addWidget(desc_general)

        auth_group = QGroupBox("Авторизация")
        auth_layout = QVBoxLayout(auth_group)

        auth_layout.addWidget(QLabel("Логин администратора:"))
        self.admin_login_input = QLineEdit()
        self.admin_login_input.setText(self.settings.get("admin_login") or "")
        auth_layout.addWidget(self.admin_login_input)

        # --- Автообновление ---
        auto_group = QGroupBox("Автообновление")
        auto_layout = QVBoxLayout(auto_group)

        self.auto_refresh_checkbox = QCheckBox("Включить автообновление")
        self.auto_refresh_checkbox.setChecked(
            self.settings.get("auto_refresh_enabled")
        )

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(30, 3600)
        self.interval_spin.setSuffix(" сек")
        self.interval_spin.setValue(
            self.settings.get("auto_refresh_interval_sec")
        )

        auto_layout.addWidget(self.auto_refresh_checkbox)
        auto_layout.addWidget(QLabel("Интервал обновления:"))
        auto_layout.addWidget(self.interval_spin)

        general_layout.addWidget(auth_group)
        general_layout.addWidget(auto_group)

        tabs.addTab(general_tab, "Общие")
        general_layout.addStretch()

        # =====================================================
        # TAB 2 — BACKEND
        # =====================================================
        backend_tab = QWidget()
        backend_layout_wrapper = QVBoxLayout(backend_tab)

        desc_backend = QLabel(
            "Настройки подключения к серверу.\n"
            "Используется ручная настройка если сервер работает на нестандартном адресе.")
        desc_backend.setWordWrap(True)
        desc_backend.setObjectName("settingsDescription")
        desc_backend.setAlignment(Qt.AlignmentFlag.AlignCenter)
        backend_layout_wrapper.insertWidget(0, desc_backend)
        backend_group = QGroupBox("Cервер")
        backend_layout = QVBoxLayout(backend_group)

        self.backend_override_checkbox = QCheckBox(
            "Ручная настройка адреса сервера"
        )
        self.backend_override_checkbox.setChecked(
            self.settings.get("backend_override_enabled")
        )

        self.backend_host_input = QLineEdit()
        self.backend_host_input.setText(self.settings.get("backend_host") or "")

        self.backend_port_spin = QSpinBox()
        self.backend_port_spin.setRange(1, 65535)
        self.backend_port_spin.setValue(
            self.settings.get("backend_port") or 0
        )

        backend_layout.addWidget(self.backend_override_checkbox)
        backend_layout.addWidget(QLabel("Адрес сервера:"))
        backend_layout.addWidget(self.backend_host_input)
        backend_layout.addWidget(QLabel("Порт сервера:"))
        backend_layout.addWidget(self.backend_port_spin)

        backend_layout_wrapper.addWidget(backend_group)

        tabs.addTab(backend_tab, "Сервер")
        backend_layout_wrapper.addStretch()

        # =====================================================
        # TAB 3 — WEB
        # =====================================================
        web_tab = QWidget()
        web_layout_wrapper = QVBoxLayout(web_tab)
        desc_web = QLabel(
            "Определяет, какие порты открываются через браузер.\n"
            "Формат: порт:протокол (например: 80:http,443:https).")
        desc_web.setWordWrap(True)
        desc_web.setObjectName("settingsDescription")
        desc_web.setAlignment(Qt.AlignmentFlag.AlignCenter)
        web_layout_wrapper.insertWidget(0, desc_web)
        web_group = QGroupBox("Web порты")
        web_layout = QVBoxLayout(web_group)

        web_layout.addWidget(QLabel("Формат: 80:http,443:https"))

        self.web_ports_input = QLineEdit()

        web_ports = self.settings.get("web_ports") or []
        formatted = [
            f'{entry["port"]}:{entry["scheme"]}'
            for entry in web_ports
        ]
        self.web_ports_input.setText(",".join(formatted))

        web_layout.addWidget(self.web_ports_input)

        web_layout_wrapper.addWidget(web_group)

        tabs.addTab(web_tab, "Порты")
        web_layout_wrapper.addStretch()

        # =====================================================
        # TAB 4 — EXTERNAL
        # =====================================================
        external_tab = QWidget()
        external_layout_wrapper = QVBoxLayout(external_tab)
        desc_external = QLabel(
            "Настройка запуска внешнего приложения для определённого порта.\n"
            "При выборе сервера с этим портом будет запущена указанная программа.")
        desc_external.setWordWrap(True)
        desc_external.setObjectName("settingsDescription")
        desc_external.setAlignment(Qt.AlignmentFlag.AlignCenter)
        external_layout_wrapper.insertWidget(0, desc_external)
        external_group = QGroupBox("Внешние приложения")
        external_layout = QVBoxLayout(external_group)

        # --- Имя ---
        external_layout.addWidget(QLabel("Имя приложения:"))
        self.external_name_input = QLineEdit()
        external_layout.addWidget(self.external_name_input)

        # --- Порт ---
        external_layout.addWidget(QLabel("Порт:"))
        self.external_port_spin = QSpinBox()
        self.external_port_spin.setRange(1, 65535)
        external_layout.addWidget(self.external_port_spin)

        # --- Путь ---
        external_layout.addWidget(QLabel("Путь к приложению:"))

        path_layout = QHBoxLayout()
        self.external_path_input = QLineEdit()

        btn_browse = QPushButton("Обзор...")
        btn_browse.clicked.connect(self._browse_external_path)

        path_layout.addWidget(self.external_path_input)
        path_layout.addWidget(btn_browse)

        external_layout.addLayout(path_layout)

        external_layout_wrapper.addWidget(external_group)

        tabs.addTab(external_tab, "Внешние приложения")
        external_layout_wrapper.addStretch()

        # Загрузка сохранённых external
        external_apps = self.settings.get("external_apps") or []
        if external_apps:
            app = external_apps[0]
            self.external_name_input.setText(app.get("name", ""))
            self.external_port_spin.setValue(app.get("port", 0))
            self.external_path_input.setText(app.get("path", ""))

        # =========================
        # КНОПКИ
        # =========================
        buttons = QHBoxLayout()

        btn_save = QPushButton("Сохранить")
        btn_cancel = QPushButton("Отмена")

        btn_save.clicked.connect(self._save_and_close)
        btn_cancel.clicked.connect(self.reject)

        buttons.addStretch()
        buttons.addWidget(btn_save)
        buttons.addWidget(btn_cancel)

        main_layout.addLayout(buttons)

        # =========================
        # SIGNALS
        # =========================
        self.auto_refresh_checkbox.toggled.connect(
            self._update_auto_refresh_enabled
        )
        self.backend_override_checkbox.toggled.connect(
            self._update_backend_enabled
        )

        self._update_auto_refresh_enabled(
            self.auto_refresh_checkbox.isChecked()
        )
        self._update_backend_enabled(
            self.backend_override_checkbox.isChecked()
        )

        # =========================
        # CONTROLLER
        # =========================
        self.controller = SettingsController(api)
        self.controller.status_changed.connect(self._set_status)
        self._set_status("unknown")
        self.controller.check_backend_status()

        # Минимальные размеры
        self.setMinimumWidth(550)
        self.setMinimumHeight(300)


    # =====================================================
    # SAVE
    # =====================================================
    def _save_and_close(self):
        self.apply()
        self.accept()

    def apply(self):
        self.settings.set("admin_login",
                          self.admin_login_input.text().strip())

        self.settings.set("auto_refresh_enabled",
                          self.auto_refresh_checkbox.isChecked())

        self.settings.set("auto_refresh_interval_sec",
                          self.interval_spin.value())

        self.settings.set("backend_override_enabled",
                          self.backend_override_checkbox.isChecked())

        self.settings.set("backend_host",
                          self.backend_host_input.text().strip())

        self.settings.set("backend_port",
                          self.backend_port_spin.value())

        # WEB
        raw = self.web_ports_input.text().strip()
        web_ports = []

        for item in raw.split(","):
            if ":" not in item:
                continue

            port_part, scheme_part = item.split(":", 1)
            port_part = port_part.strip()
            scheme_part = scheme_part.strip().lower()

            if port_part.isdigit() and scheme_part in ("http", "https"):
                web_ports.append({
                    "port": int(port_part),
                    "scheme": scheme_part
                })

        self.settings.set("web_ports", web_ports)

        # EXTERNAL
        external_apps = []
        name = self.external_name_input.text().strip()
        port = self.external_port_spin.value()
        path = self.external_path_input.text().strip()

        if name and port and path:
            if not os.path.exists(path):
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    "Указанный путь к приложению не существует."
                )
            else:
                external_apps.append({
                    "name": name,
                    "port": port,
                    "path": path
                })

        self.settings.set("external_apps", external_apps)
        self.settings.save()

    # =====================================================
    # HELPERS
    # =====================================================
    def _browse_external_path(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите приложение",
            "",
            "Executable (*.exe);;All files (*)"
        )
        if file_path:
            self.external_path_input.setText(file_path)

    def _update_auto_refresh_enabled(self, enabled: bool):
        self.interval_spin.setEnabled(enabled)

    def _update_backend_enabled(self, enabled: bool):
        self.backend_host_input.setEnabled(enabled)
        self.backend_port_spin.setEnabled(enabled)

    def _set_status(self, status: str):
        icons = {
            "ok": ("status_ok_icon.png", "Сервер доступен"),
            "degraded": ("status_warn_icon.png", "Некоторые сервисы недоступны"),
            "offline": ("status_offline_icon.png", "Сервер недоступен"),
            "unknown": ("status_unknown.png", "Проверка сервера...")
        }

        icon, text = icons.get(status, icons["unknown"])

        self.status_icon.setPixmap(
            QIcon(os.path.join(ICONS_DIR, icon)).pixmap(16, 16)
        )
        self.status_text.setText(text)