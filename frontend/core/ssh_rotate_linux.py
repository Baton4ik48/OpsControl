import ctypes
import shlex
import socket
import sys
import paramiko
from paramiko.ssh_exception import (
    NoValidConnectionsError,
    AuthenticationException,
    SSHException,
)

class SSHRotateError(Exception):
    pass

def _wipe(s: str) -> None:
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

def _try_auth(host: str, port: int, username: str, password: str, timeout: int):
    """
    Проверяет, работает ли пароль для SSH-входа.
    Используется для верификации после разрыва канала.

    Возвращает:
      True  — пароль подходит
      False — пароль точно неверный (AuthenticationException)
      None  — невозможно определить (таймаут, сеть недоступна, прочие ошибки)
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname=host,
            port=port,
            username=username,
            password=password,
            timeout=timeout,
            allow_agent=False,
            look_for_keys=False,
        )
        return True
    except AuthenticationException:
        return False
    except Exception:
        return None  # таймаут, разрыв сети, прочие — неизвестно
    finally:
        client.close()

def rotate_linux_password(
    host: str,
    username: str,
    current_password: str,
    new_password: str,
    port: int = 22,
    timeout: int = 10,
) -> None:
    """
    Подключается по SSH и меняет пароль пользователя через chpasswd.

    Использует printf + sudo без PTY:
      - printf передаёт username:new_password в chpasswd через pipe
      - PTY не используется — исключает эхо паролей в stdout
      - Требует NOPASSWD для chpasswd в sudoers

    Если канал рвётся во время выполнения команды — делает проверочное
    переподключение:
      - новый пароль работает  → смена прошла успешно, возвращаем управление
      - старый пароль работает → смена не прошла, бросаем SSHRotateError (безопасно)
      - ни один не работает    → неизвестное состояние, бросаем SSHRotateError

    Бросает SSHRotateError во всех случаях неуспеха.
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    channel_dropped = False

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
            raise SSHRotateError(
                "Ошибка аутентификации SSH — неверные текущие учётные данные"
            )
        except NoValidConnectionsError:
            raise SSHRotateError(f"Не удалось подключиться к {host}:{port}")
        except (SSHException, socket.timeout, TimeoutError, OSError) as e:
            raise SSHRotateError(f"SSH ошибка при подключении: {e}")

        # sudo -S читает пароль из stdin (первая строка), остальное идёт в chpasswd.
        # Работает как с NOPASSWD так и без него.
        command = (
            f"printf '%s\\n%s:%s\\n' {shlex.quote(current_password)} "
            f"{shlex.quote(username)} {shlex.quote(new_password)} "
            f"| sudo -S chpasswd 2>&1"
        )

        try:
            stdin, stdout, _ = client.exec_command(command, timeout=15)
            stdin.channel.shutdown_write()
            raw_output = stdout.read().decode().strip()
            exit_code = stdout.channel.recv_exit_status()
        except (SSHException, socket.timeout, TimeoutError, EOFError, OSError):
            channel_dropped = True
        else:
            if exit_code != 0:
                real_error = "\n".join(
                    line
                    for line in raw_output.splitlines()
                    if not any(
                        s in line.lower() for s in ["password for", "пароль для"]
                    )
                ).strip()
                raise SSHRotateError(
                    f"Ошибка смены пароля: {real_error or f'exit code {exit_code}'}"
                )

    finally:
        client.close()

    if not channel_dropped:
        return

    # Важно различать три случая:
    #   True  — пароль точно работает
    #   False — пароль точно НЕ работает (сервер ответил AuthenticationException)
    #   None  — соединение не установилось (таймаут / сеть), состояние неизвестно
    verify_timeout = min(timeout, 5)

    new_result = _try_auth(host, port, username, new_password, verify_timeout)

    if new_result is True:
        # Новый пароль работает — смена прошла успешно, продолжаем
        return

    if new_result is None:
        # Сеть недоступна для верификации — не знаем, изменился ли пароль
        raise SSHRotateError(
            "Соединение разорвано, и проверочное подключение не удалось (таймаут).\n"
            "Невозможно определить состояние пароля — проверьте сервер вручную."
        )

    # new_result is False — новый пароль точно неверный, пробуем старый
    old_result = _try_auth(host, port, username, current_password, verify_timeout)

    if old_result is True:
        raise SSHRotateError(
            "Соединение разорвано во время выполнения команды.\n"
            "Пароль не был изменён — повторите попытку."
        )

    if old_result is None:
        raise SSHRotateError(
            "Соединение разорвано. Новый пароль не работает, "
            "проверить старый не удалось (таймаут).\n"
            "Проверьте сервер вручную."
        )

    # Оба пароля вернули AuthenticationException — нештатная ситуация
    raise SSHRotateError(
        "Соединение разорвано. Ни новый, ни старый пароль не подходят.\n"
        "Возможно, пароль был изменён третьей стороной — проверьте сервер вручную."
    )
