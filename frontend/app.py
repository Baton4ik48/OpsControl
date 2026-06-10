import sys

# import os
from PyQt6.QtWidgets import QApplication

# from PyQt6.QtGui import QIcon
from core.utils.loader_styles import load_styles
from ui.main_window import MainWindow
from core.logger import setup_logging

# from core.paths import ICONS_DIR

def run():
    setup_logging()

    app = QApplication(sys.argv)

    # app.setWindowIcon(QIcon(os.path.join(ICONS_DIR, "app_icon.png")))

    app.setStyle("Fusion")
    app.setStyleSheet(load_styles())

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
