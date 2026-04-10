import sys
from PyQt6.QtWidgets import QApplication
from core.utils.loader_styles import load_styles
from ui.main_window import MainWindow
from core.logger import setup_logging

def run():
    setup_logging()

    app = QApplication(sys.argv)

    app.setStyle("Fusion")

    app.setStyleSheet(load_styles())

    window = MainWindow()
    window.show()

    sys.exit(app.exec())