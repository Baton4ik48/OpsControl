import logging
import os
from logging.handlers import RotatingFileHandler
from core.paths import LOG_DIR

os.makedirs(LOG_DIR, exist_ok=True)

class MaxLevelFilter(logging.Filter):
    def __init__(self, max_level):
        super().__init__()
        self.max_level = max_level

    def filter(self, record):
        return record.levelno <= self.max_level

def _create_handler(filename, level, max_level=None):
    handler = RotatingFileHandler(
        os.path.join(LOG_DIR, filename),
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    handler.setLevel(level)

    if max_level is not None:
        handler.addFilter(MaxLevelFilter(max_level))

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    handler.setFormatter(formatter)
    return handler

def setup_logging():
    root = logging.getLogger()

    if root.handlers:
        return

    root.setLevel(logging.DEBUG)

    root.addHandler(
        _create_handler("app.log", level=logging.INFO, max_level=logging.WARNING)
    )

    # errors.log: ERROR +
    root.addHandler(_create_handler("errors.log", level=logging.ERROR))

def get_logger(name: str):
    return logging.getLogger(name)
