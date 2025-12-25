from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton, QLabel, QAbstractItemView, QPushButton, QFileDialog, QMessageBox
from PyQt6.QtCore import QTimer
import pandas as pd
import os
from functional.import_xlsx_to_sqliteBD import import_excel_to_db

class AutoRefreshPanel(QWidget):
    """
    Панель автообновления, отдельный виджет.
    Управляет таймером и вызывает update_all() у MainWindow.
    """

    def __init__(self, parent):
        super().__init__()
        self.parent = parent   # ссылка на MainWindow
        

        layout = QHBoxLayout(self)

        self.import_xlsx = QPushButton("Add to BD")
        self.import_xlsx.setFixedWidth(100)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Время (мин)")
        self.input.setFixedWidth(100)

        self.btn = QPushButton("ok")
        self.btn.setFixedWidth(30)

        self.status = QLabel("Автообновление: выкл")

        self.timer = QTimer()
        self.timer.timeout.connect(self._tick)

        layout.addWidget(self.import_xlsx)
        layout.addWidget(self.input)
        layout.addWidget(self.btn)
        layout.addWidget(self.status)

        self.import_xlsx.clicked.connect(self.import_xlsx_to_db)
        self.btn.clicked.connect(self.apply_interval)
        self.remaining = 0

    def apply_interval(self):
        """
        Устанавливаем интервал автообновления.
        """
        try:
            seconds = int(self.input.text())
        except ValueError:
            self.status.setText("Ошибка: вводите число")
            return

        if seconds <= 0:
            self.timer.stop()
            self.status.setText("Автообновление: выкл")
            return

        self.remaining = seconds
        self.status.setText(f"Следующее обновление через: {self.remaining} сек")

        self.timer.start(1000)

    def _tick(self):
        """
        Обратный отсчёт.
        """
        self.remaining -= 1

        if self.remaining <= 0:
            self.status.setText("Обновление...")
            self.parent.update_all_servers()   # <<< вызывание общей проверки

            # сбрасываем таймер
            try:
                interval = int(self.input.text())
            except:
                interval = 0

            if interval <= 0:
                self.timer.stop()
                self.status.setText("Автообновление: выкл")
            else:
                self.remaining = interval

        else:
            self.status.setText(f"Следующее обновление через: {self.remaining} сек")

    def import_xlsx_to_db(self):
        # 1. Выбор файла через диалог
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите Excel файл",
            "",
            "Excel Files (*.xlsx *.xls)"
        )
        if not file_path:
            return  # пользователь отменил

        # 2. Попытка загрузки файла через pandas
        try:
            df = pd.read_excel(file_path)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть файл: {e}")
            return

        # 3. Проверка столбцов
        required_columns = ["BranchName", "ServerName", "ServerIP", "PortNumber"]
        for col in required_columns:
            if col not in df.columns:
                QMessageBox.critical(self, "Ошибка", f"Отсутствует обязательный столбец: {col}")
                return

        # 4. Проверка на пустые значения
        if df[required_columns].isnull().any().any():
            QMessageBox.critical(self, "Ошибка", "Есть пустые обязательные поля!")
            return

        # 5. Внесение данных в БД
        import_excel_to_db(file_path, os.path.join(os.path.dirname(__file__), "..", "bin", "database.db"), "Servers")

        # 6. Обновление таблицы в интерфейсе
        self.parent.load_devices_from_db()

        QMessageBox.information(self, "Готово", "Импорт завершён успешно!")
