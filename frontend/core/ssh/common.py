import socket

import paramiko
from paramiko.ssh_exception import (
    NoValidConnectionsError,
    AuthenticationException,
    SSHException,
)


class SSHRotateError(Exception):
    pass


def connect_or_raise(
    host: str, port: int, username: str, password: str, timeout: int
) -> paramiko.SSHClient:
    """
    Подключается по SSH, переводя ошибки paramiko в SSHRotateError
    с понятными пользователю сообщениями.
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
    except AuthenticationException:
        client.close()
        raise SSHRotateError(
            "Ошибка аутентификации SSH — неверные текущие учётные данные"
        )
    except NoValidConnectionsError:
        client.close()
        raise SSHRotateError(f"Не удалось подключиться к {host}:{port}")
    except (SSHException, socket.timeout, TimeoutError, OSError) as e:
        client.close()
        raise SSHRotateError(f"SSH ошибка при подключении: {e}")
    return client


def try_auth(host: str, port: int, username: str, password: str, timeout: int):
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
