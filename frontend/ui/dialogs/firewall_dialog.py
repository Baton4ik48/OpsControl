import os

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTextEdit,
    QFileDialog,
    QMessageBox,
)
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtCore import Qt

from core.firewall_generator import generate_firewall_rules
from core.paths import FIREWALL_TEMPLATE_PATH

README_TEXT = """
===========================================================
                xFirewall Rule Generator
===========================================================

Назначение:
Генерация команд firewall forward add из Excel-файла.

Структура Excel:

A1 — Номер заявки (rule "NAME")
С 3 строки — правила.

B — src ip (IP-адрес откуда)
E — ports raw:
      tcp:22
      tcp:443
      tcp:9200
F — dst ip (IP-адрес куда)

Каждая строка Excel = одна команда firewall.
Формат: firewall forward add <id> rule "NAME" src <ip> dst <ip> tcp dport <port> ... pass
"""


class FirewallDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Генератор firewall правил")

        screen = QGuiApplication.primaryScreen().availableGeometry()
        self.resize(int(screen.width() * 0.6), int(screen.height() * 0.6))

        # Можно разворачивать
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint)

        self.generated_filename = "firewall_rule.txt"

        layout = QVBoxLayout(self)

        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.text.setPlainText(README_TEXT)
        layout.addWidget(self.text)

        buttons_layout = QHBoxLayout()

        buttons_layout.addStretch()

        btn_template = QPushButton("Открыть шаблон")
        btn_template.setFixedWidth(160)
        btn_template.clicked.connect(self.open_template)
        buttons_layout.addWidget(btn_template)

        btn_load = QPushButton("Сгенерировать")
        btn_load.setFixedWidth(160)
        btn_load.clicked.connect(self.load_excel)
        buttons_layout.addWidget(btn_load)

        btn_save = QPushButton("Сохранить")
        btn_save.setFixedWidth(140)
        btn_save.clicked.connect(self.save_result)
        buttons_layout.addWidget(btn_save)

        buttons_layout.addStretch()

        layout.addLayout(buttons_layout)

    # ------------------------------------------------------

    def open_template(self):
        if not os.path.exists(FIREWALL_TEMPLATE_PATH):
            QMessageBox.warning(self, "Шаблон не найден", "Файл шаблона отсутствует.")
            return

        os.startfile(FIREWALL_TEMPLATE_PATH)

    # ------------------------------------------------------

    def load_excel(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите Excel файл", "", "Excel Files (*.xlsx)"
        )

        if not file_path:
            return

        try:
            commands = generate_firewall_rules(file_path)

            if not commands:
                QMessageBox.warning(self, "Нет правил", "В файле не найдено правил.")
                return

            self.text.setPlainText("\n".join(commands))

            # имя файла по номеру заявки
            rule_name = commands[0].split('rule "')[1].split('"')[0]
            self.generated_filename = f"firewall_{rule_name}.txt"

            QMessageBox.information(
                self, "Готово", f"Сгенерировано правил: {len(commands)}"
            )

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    # ------------------------------------------------------

    def save_result(self):
        content = self.text.toPlainText()
        if not content.strip():
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить файл", self.generated_filename, "Text Files (*.txt)"
        )

        if not save_path:
            return

        with open(save_path, "w", encoding="utf-8") as f:
            f.write(content)

        QMessageBox.information(self, "Готово", "Файл сохранён.")
