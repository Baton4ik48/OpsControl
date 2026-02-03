from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPlainTextEdit,
    QLineEdit
)
from PyQt6.QtCore import Qt


class Console(QWidget):
    def __init__(self):
        super().__init__()

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setMaximumBlockCount(1000)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Введите команду…")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        layout.addWidget(self.output)
        layout.addWidget(self.input)

        # history
        self._history = []
        self._history_index = -1

        # controller будет подключён извне
        self._handler = None

        # сигналы
        self.input.returnPressed.connect(self._on_enter)
        self.input.installEventFilter(self)

    # ==========================
    # PUBLIC API
    # ==========================

    def set_handler(self, handler):
        self._handler = handler

    def log(self, text: str):
        if text == "__clear__":
            self.output.clear()
            return

        self.output.appendPlainText(text)
        self.output.verticalScrollBar().setValue(
            self.output.verticalScrollBar().maximum()
        )

    # ==========================
    # INPUT
    # ==========================

    def _on_enter(self):
        text = self.input.text().strip()
        if not text:
            return

        self.log(f"> {text}")

        self._history.append(text)
        self._history_index = len(self._history)

        self.input.clear()

        if self._handler:
            self._handler(text)

    # ==========================
    # HISTORY ↑ ↓
    # ==========================

    def eventFilter(self, obj, event):
        if obj is self.input and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key.Key_Up:
                self._history_up()
                return True

            if event.key() == Qt.Key.Key_Down:
                self._history_down()
                return True

        return super().eventFilter(obj, event)

    def _history_up(self):
        if not self._history:
            return

        self._history_index = max(0, self._history_index - 1)
        self.input.setText(self._history[self._history_index])

    def _history_down(self):
        if not self._history:
            return

        self._history_index += 1

        if self._history_index >= len(self._history):
            self._history_index = len(self._history)
            self.input.clear()
        else:
            self.input.setText(self._history[self._history_index])
