import shlex
import socket

from paramiko.ssh_exception import SSHException

from core.ssh.common import SSHRotateError, connect_or_raise, try_auth


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
    client = connect_or_raise(host, port, username, current_password, timeout)
    channel_dropped = False

    try:
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

    new_result = try_auth(host, port, username, new_password, verify_timeout)

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
    old_result = try_auth(host, port, username, current_password, verify_timeout)

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
