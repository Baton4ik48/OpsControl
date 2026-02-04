import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QCheckBox, QSpinBox, QLabel, QPushButton, QHBoxLayout, QLineEdit, QGroupBox)
from PyQt6.QtGui import QIcon

from core.paths import ICONS_DIR

class SettingsDialog(QDialog):
    def __init__(self, settings):
        super().__init__()

        self.settings = settings
        self.setWindowIcon(QIcon(os.path.join(ICONS_DIR, "settings_icon.png")))
        self.setWindowTitle("Настройки")
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)


        # =========================
        # АВТОРИЗАЦИЯ
        # =========================
        auth_group = QGroupBox("Авторизация")
        auth_layout = QVBoxLayout(auth_group)

        auth_layout.addWidget(QLabel("Логин администратора:"))
        self.admin_login_input = QLineEdit()
        self.admin_login_input.setPlaceholderText("AdminGTM")
        self.admin_login_input.setText(
            self.settings.get("admin_login") or ""
        )
        
        auth_layout.addWidget(self.admin_login_input)
        layout.addWidget(auth_group)


        # =========================
        # АВТООБНОВЛЕНИЕ
        # =========================
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

        layout.addWidget(auto_group)

        # =========================
        # BACKEND
        # =========================
        backend_group = QGroupBox("Backend сервер")
        backend_layout = QVBoxLayout(backend_group)

        self.backend_override_checkbox = QCheckBox(
            "Ручная настройка адреса сервера"
        )
        self.backend_override_checkbox.setChecked(
            self.settings.get("backend_override_enabled")
        )

        self.backend_host_input = QLineEdit()
        self.backend_host_input.setPlaceholderText("host (например: 127.0.0.1)")
        self.backend_host_input.setText(
            self.settings.get("backend_host")
        )

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

        layout.addWidget(backend_group)

        # =========================
        # КНОПКИ
        # =========================
        buttons = QHBoxLayout()

        btn_save = QPushButton("Сохранить")
        btn_cancel = QPushButton("Отмена")

        btn_save.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)

        buttons.addStretch()
        buttons.addWidget(btn_save)
        buttons.addWidget(btn_cancel)

        layout.addLayout(buttons)

        # =========================
        # ЛОГИКА ВКЛ / ВЫКЛ
        # =========================
        self.auto_refresh_checkbox.toggled.connect(self._update_auto_refresh_enabled)
        self._update_auto_refresh_enabled(self.auto_refresh_checkbox.isChecked())

        self.backend_override_checkbox.toggled.connect(self._update_backend_enabled)
        self._update_backend_enabled(self.backend_override_checkbox.isChecked())

    # =========================
    # APPLY
    # =========================
    def apply(self):
        # логин
        self.settings.set(
            "admin_login", 
            self.admin_login_input.text().strip()
        )
        # автообновление
        self.settings.set(
            "auto_refresh_enabled",
            self.auto_refresh_checkbox.isChecked()
        )
        self.settings.set(
            "auto_refresh_interval_sec",
            self.interval_spin.value()
        )

        # backend override
        self.settings.set(
            "backend_override_enabled",
            self.backend_override_checkbox.isChecked()
        )
        self.settings.set(
            "backend_host",
            self.backend_host_input.text().strip()
        )
        self.settings.set(
            "backend_port",
            self.backend_port_spin.value()
        )

        self.settings.save()

    # =========================
    # UI HELPERS
    # =========================
    def _update_auto_refresh_enabled(self, enabled: bool):
        self.interval_spin.setEnabled(enabled)

    def _update_backend_enabled(self, enabled: bool):
        self.backend_host_input.setEnabled(enabled)
        self.backend_port_spin.setEnabled(enabled)