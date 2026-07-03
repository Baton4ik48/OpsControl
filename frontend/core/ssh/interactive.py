"""
Общий каркас смены пароля на сетевых устройствах (Cisco, Nateks, …)
через интерактивный SSH-shell.

Устройство-специфичная часть — только последовательность команд/промптов
(параметр flow), всё остальное (подключение, обработка разрыва канала,
проверочное переподключение) одинаково для всех устройств.
"""

import re
import socket
import time

from paramiko.ssh_exception import SSHException

from core.ssh.common import SSHRotateError, connect_or_raise, try_auth

# ANSI escape-последовательности — встречаются в выводе некоторых устройств
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[mGKHABCDJr]")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def wait_prompt(channel, expected: str, timeout: int = 15) -> str:
    """
    Читает вывод канала до появления ожидаемого промпта в конце строки.

    Возвращает накопленный вывод.
    Бросает SSHRotateError по таймауту или закрытию канала.
    """
    buf = ""
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        if channel.recv_ready():
            chunk = channel.recv(4096).decode("utf-8", errors="replace")
            buf += chunk
            clean = _strip_ansi(buf)
            if clean.rstrip().endswith(expected):
                return buf
        elif channel.closed or channel.exit_status_ready():
            raise SSHRotateError(
                f"Канал закрылся при ожидании промпта '{expected}'.\n"
                f"Последний вывод: {buf[-300:]!r}"
            )
        else:
            time.sleep(0.05)

    raise SSHRotateError(
        f"Таймаут ({timeout}с) ожидания промпта '{expected}'.\n"
        f"Последний вывод: {buf[-300:]!r}"
    )


def wait_prompt_either(channel, options: tuple, timeout: int) -> str:
    """
    Ждёт любого из перечисленных промптов, возвращает тот, что совпал.

    Нужен для начального подключения к Cisco: пользователь с privilege 15
    попадает сразу в '#', с privilege 1 — в '>'.
    """
    buf = ""
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        if channel.recv_ready():
            chunk = channel.recv(4096).decode("utf-8", errors="replace")
            buf += chunk
            clean = _strip_ansi(buf).rstrip()
            for opt in options:
                if clean.endswith(opt):
                    return opt
        elif channel.closed or channel.exit_status_ready():
            raise SSHRotateError(
                f"Канал закрылся при ожидании промпта {options!r}.\n"
                f"Последний вывод: {buf[-300:]!r}"
            )
        else:
            time.sleep(0.05)

    raise SSHRotateError(
        f"Таймаут ({timeout}с) ожидания промпта {options!r}.\n"
        f"Последний вывод: {buf[-300:]!r}"
    )


def rotate_cli_password(
    host: str,
    username: str,
    current_password: str,
    new_password: str,
    port: int,
    timeout: int,
    flow,
    save_command: str,
) -> None:
    """
    Меняет пароль на устройстве через интерактивный SSH-shell.

    flow(channel, timeout) — устройство-специфичная последовательность команд;
    должна довести устройство до сохранения конфига.
    save_command — имя команды сохранения (для текста предупреждения,
    если канал разорвался и неизвестно, успела ли она выполниться).

    Если канал рвётся в процессе — делается проверочное переподключение
    с новым паролем.

    Бросает SSHRotateError во всех случаях неуспеха.
    """
    client = connect_or_raise(host, port, username, current_password, timeout)

    try:
        try:
            channel = client.invoke_shell()
            channel.settimeout(timeout)
        except SSHException as e:
            raise SSHRotateError(f"Не удалось открыть интерактивный shell: {e}")

        channel_dropped = False
        try:
            flow(channel, timeout)
        except (SSHException, socket.timeout, TimeoutError, EOFError, OSError):
            channel_dropped = True
        finally:
            channel.close()

    finally:
        client.close()

    if not channel_dropped:
        return

    # Если канал разорвался посередине — неизвестно на каком шаге.
    # Проверяем новым паролем: если заходит — пароль точно сменён.
    # Важно: даже если save_command не выполнился, пароль будет работать
    # до перезагрузки. Пользователь получит предупреждение.
    verify_timeout = min(timeout, 5)

    new_result = try_auth(host, port, username, new_password, verify_timeout)

    if new_result is True:
        raise SSHRotateError(
            "Соединение разорвано во время настройки.\n"
            f"Новый пароль работает, но команда {save_command} могла не выполниться.\n"
            f"Войдите на устройство и выполните {save_command} вручную для сохранения конфига."
        )

    if new_result is None:
        raise SSHRotateError(
            "Соединение разорвано, и проверочное подключение не удалось (таймаут).\n"
            "Невозможно определить состояние пароля — проверьте устройство вручную."
        )

    # Новый пароль не работает — пробуем старый
    old_result = try_auth(host, port, username, current_password, verify_timeout)

    if old_result is True:
        raise SSHRotateError(
            "Соединение разорвано. Пароль не был изменён — повторите попытку."
        )

    if old_result is None:
        raise SSHRotateError(
            "Соединение разорвано. Новый пароль не работает, "
            "проверить старый не удалось (таймаут).\n"
            "Проверьте устройство вручную."
        )

    raise SSHRotateError(
        "Соединение разорвано. Ни новый, ни старый пароль не подходят.\n"
        "Возможно, пароль был изменён третьей стороной — проверьте устройство вручную."
    )
