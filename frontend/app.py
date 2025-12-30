import sys
from PyQt6.QtWidgets import QApplication
from ui.styles.loader import load_styles
from ui.main_window import MainWindow

def run():
    app = QApplication(sys.argv)
    app.setStyleSheet(load_styles())
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
