import ctypes
import sys


def wipe(s: str) -> None:
    """
    Перезаписывает внутренний буфер строки нулями в памяти процесса.
    CPython 3.x, 64-bit, best-effort — защита от дампа памяти.

    Принцип: sys.getsizeof('') возвращает размер заголовка PyASCIIObject
    включая null-терминатор. Данные строки начинаются с offset = getsizeof('') - 1.
    Работает корректно для compact ASCII (все генерируемые пароли).
    """
    if not s:
        return
    try:
        offset = sys.getsizeof("") - 1
        ctypes.memset(id(s) + offset, 0, len(s))
    except Exception:
        pass
