from PyQt6.QtWidgets import QPlainTextEdit
from PyQt6.QtCore import Qt

class ConsoleWidget(QPlainTextEdit):
    def __init__(self, command_callback, password_mode_callback=None):
        super().__init__()
        self.command_callback = command_callback
        self.password_mode_callback = password_mode_callback
        self.prompt = "> "

        self.password_mode = False  # флаг "ввод пароля"

        self.setReadOnly(False)
        self.insertPrompt()

    def set_password_mode(self, enabled: bool):
        self.password_mode = enabled

    def insertPrompt(self):
        cursor = self.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(self.prompt)
        self.setTextCursor(cursor)

    def get_current_command(self):
        text = self.toPlainText().split("\n")[-1]
        if text.startswith(self.prompt):
            return text[len(self.prompt):]
        return ""

    def add_log(self, text):
        if text == "__clear_console__":
            self.setPlainText(self.prompt)
            return

        cursor = self.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(f"\n{text}\n{self.prompt}")
        self.setTextCursor(cursor)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            cmd = self.get_current_command()

            # пароль — скрытый ввод
            if self.password_mode:
                self.command_callback(cmd)
                self.password_mode = False

            else:
                self.command_callback(cmd)

            cursor = self.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            cursor.insertText("\n" + self.prompt)
            self.setTextCursor(cursor)
            return

        # скрываем ввод пароля
        if self.password_mode:
            if event.text():
                cursor = self.textCursor()
                cursor.insertText("*")  # отображаем *
            return

        super().keyPressEvent(event)
