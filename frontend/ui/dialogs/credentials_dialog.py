from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
)
from PyQt6.QtCore import pyqtSignal, QTimer

class CredentialsDialog(QDialog):
    submitted = pyqtSignal(str)

    def __init__(self, ip: str = "", port: int = 0, mode: str = "show"):
        super().__init__()

        self.mode = mode

        if mode == "ssh":
            self.setWindowTitle(f"SSH подключение {ip}:{port}")
        elif mode == "infra":
            self.setWindowTitle("Доступ к управлению инфраструктурой")
        elif mode == "envelope":
            self.setWindowTitle("Формирование конверта с паролями")
        else:
            self.setWindowTitle(f"Учётные данные {ip}:{port}")
        self.setModal(True)

        layout = QVBoxLayout(self)

        if mode == "ssh":
            layout.addWidget(
                QLabel("Введите мастер-пароль для подключения к серверу(SSH):")
            )
        elif mode == "infra":
            layout.addWidget(
                QLabel(
                    "Введите мастер-пароль для доступа к управлению инфраструктурой:"
                )
            )
        elif mode == "envelope":
            layout.addWidget(
                QLabel("Введите мастер-пароль для выгрузки учётных данных:")
            )
        else:
            layout.addWidget(QLabel("Введите пароль администратора:"))

        self.admin_input = QLineEdit()
        self.admin_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.admin_input.returnPressed.connect(self._on_submit)
        layout.addWidget(self.admin_input)

        btn_label = "Войти" if mode == "infra" else ("Сформировать" if mode == "envelope" else "Показать")
        self.show_btn = QPushButton(btn_label)
        self.show_btn.clicked.connect(self._on_submit)
        layout.addWidget(self.show_btn)

        # Ширина окна — title bar использует системный шрифт, считаем по символам
        min_w = max(320, len(self.windowTitle()) * 11 + 160)
        self.setMinimumWidth(min_w)

    def _on_submit(self):
        password = self.admin_input.text().strip()
        if not password:
            QMessageBox.warning(self, "Ошибка", "Введите пароль администратора")
            return

        self.admin_input.clear()
        self.accept()
        # Откладываем сигнал на следующую итерацию event loop, чтобы exec() этого диалога
        # полностью завершился до открытия следующего (избегаем вложенных event loop).
        QTimer.singleShot(0, lambda: self.submitted.emit(password))
