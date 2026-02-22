from PyQt6.QtWidgets import QWidget, QFormLayout, QLineEdit, QPushButton
from PyQt6.QtCore import pyqtSignal


class BranchForm(QWidget):
    saved = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        layout = QFormLayout(self)

        self.name_input = QLineEdit()

        layout.addRow("Название филиала:", self.name_input)

        self.save_btn = QPushButton("Сохранить")
        layout.addRow(self.save_btn)

        self.save_btn.clicked.connect(self._on_save)

    def set_data(self, data: dict):
        self.name_input.setText(data["name"])

    def _on_save(self):
        name = self.name_input.text().strip()

        if not name:
            self.error.emit("Название не может быть пустым")
            return

        self.saved.emit(name)