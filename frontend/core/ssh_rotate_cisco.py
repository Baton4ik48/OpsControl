import re
import socket
import time
import paramiko
from paramiko.ssh_exception import NoValidConnectionsError, AuthenticationException, SSHException

from core.ssh_rotate_linux import SSHRotateError, _try_auth


# ANSI escape-последовательности — встречаются в выводе некоторых устройств
_ANSI_RE = re.compile(r'\x1b\[[0-9;]*[mGKHABCDJr]')


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub('', text)


def _wait_prompt(channel, expected: str, timeout: int = 15) -> str:
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


def _wait_prompt_either(channel, options: tuple, timeout: int) -> str:
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


def rotate_cisco_password(
    host: str,
    username: str,
    current_password: str,
    new_password: str,
    port: int = 22,
    timeout: int = 15,
) -> None:
    """
    Меняет пароль пользователя на коммутаторе Cisco 2960/2950 через интерактивный SSH.

    Последовательность команд:
      connect → hostname> (privilege 1) или hostname# (privilege 15) →
      [если >]: enable → hostname# →
      configure terminal → hostname(config)# →
      username <user> password <pass> → hostname(config)# →
      end     → hostname# →
      write memory → hostname# → disconnect

    Cisco IOS использует стандартный промпт `hostname(config)#`.
    Команда входа в конфиг: `configure terminal` (не `config`).
    Команда сохранения: `write memory`.

    ВАЖНО: пароль передаётся plaintext напрямую в CLI-команду.
    Не используется shlex.quote — CLI устройства не является shell,
    кавычки были бы приняты как часть пароля.

    Если канал рвётся в процессе — делается проверочное переподключение
    с новым паролем.

    Бросает SSHRotateError во всех случаях неуспеха.
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        try:
            client.connect(
                hostname=host,
                port=port,
                username=username,
                password=current_password,
                timeout=timeout,
                allow_agent=False,
                look_for_keys=False,
            )
        except AuthenticationException:
            raise SSHRotateError("Ошибка аутентификации SSH — неверные текущие учётные данные")
        except NoValidConnectionsError:
            raise SSHRotateError(f"Не удалось подключиться к {host}:{port}")
        except (SSHException, socket.timeout, TimeoutError, OSError) as e:
            raise SSHRotateError(f"SSH ошибка при подключении: {e}")

        try:
            channel = client.invoke_shell()
            channel.settimeout(timeout)
        except SSHException as e:
            raise SSHRotateError(f"Не удалось открыть интерактивный shell: {e}")

        channel_dropped = False
        try:
            # Cisco с privilege 15 сразу даёт '#', с privilege 1 — '>'
            initial = _wait_prompt_either(channel, (">", "#"), timeout)

            if initial == ">":
                channel.send("enable\n")
                _wait_prompt(channel, "#", timeout)

            # На Cisco: 'configure terminal', не 'config'
            channel.send("configure terminal\n")
            _wait_prompt(channel, "(config)#", timeout)

            # Пароль передаётся plaintext — кавычки НЕ используются,
            # устройство воспримет их как часть пароля
            channel.send(f"username {username} password {new_password}\n")
            _wait_prompt(channel, "(config)#", timeout)

            # end — выходим сразу в privileged exec, минуя промежуточные уровни
            channel.send("end\n")
            _wait_prompt(channel, "#", timeout)

            # Сохранение running-config → startup-config
            channel.send("write memory\n")
            _wait_prompt(channel, "#", timeout)

        except (SSHException, socket.timeout, TimeoutError, EOFError, OSError):
            channel_dropped = True
        finally:
            channel.close()

    finally:
        client.close()

    if not channel_dropped:
        return

    # ── Верификация после разрыва канала ──────────────────────────────────────
    # Если канал разорвался посередине — неизвестно на каком шаге.
    # Проверяем новым паролем: если заходит — пароль точно сменён.
    # Важно: даже если `write memory` не выполнился, пароль будет работать до перезагрузки.
    # Пользователь получит предупреждение.
    verify_timeout = min(timeout, 5)

    new_result = _try_auth(host, port, username, new_password, verify_timeout)

    if new_result is True:
        raise SSHRotateError(
            "Соединение разорвано во время настройки.\n"
            "Новый пароль работает, но команда write memory могла не выполниться.\n"
            "Войдите на устройство и выполните write memory вручную для сохранения конфига."
        )

    if new_result is None:
        raise SSHRotateError(
            "Соединение разорвано, и проверочное подключение не удалось (таймаут).\n"
            "Невозможно определить состояние пароля — проверьте устройство вручную."
        )

    # Новый пароль не работает — пробуем старый
    old_result = _try_auth(host, port, username, current_password, verify_timeout)

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
