import shlex
import paramiko
from paramiko.ssh_exception import (
    NoValidConnectionsError,
    AuthenticationException,
    SSHException,
)
from app.logging import get_logger

logger = get_logger("ssh_rotate")


def _sh_escape(value: str) -> str:
    """Безопасно экранирует строку для передачи в shell-команду."""
    return shlex.quote(value)


class SSHRotateError(Exception):
    pass


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
    Бросает SSHRotateError если что-то пошло не так.
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        logger.info(f"SSH connect → {host}:{port} as {username}")

        client.connect(
            hostname=host,
            port=port,
            username=username,
            password=current_password,
            timeout=timeout,
            allow_agent=False,
            look_for_keys=False,
        )

        # sudo -S читает пароль из stdin ДО pipe.
        # Передаём через printf: первая строка — пароль для sudo, вторая — для chpasswd.
        # printf используем вместо echo чтобы избежать проблем со спецсимволами.
        command = (
            f"printf '%s\\n%s:%s\\n' {_sh_escape(current_password)} "
            f"{_sh_escape(username)} {_sh_escape(new_password)} "
            f"| sudo -S chpasswd 2>&1"
        )

        logger.debug(f"Running chpasswd command on {host}")
        stdin, stdout, stderr = client.exec_command(command, timeout=15)
        stdin.channel.shutdown_write()

        raw_output = stdout.read().decode().strip()
        exit_code = stdout.channel.recv_exit_status()

        logger.debug(f"chpasswd exit={exit_code}, output: {raw_output!r}")

        if exit_code != 0:
            # фильтруем нормальный sudo prompt из вывода
            real_error = "\n".join(
                line
                for line in raw_output.splitlines()
                if not any(s in line.lower() for s in ["password for", "пароль для"])
            ).strip()
            logger.error(f"chpasswd failed (exit={exit_code}): {raw_output!r}")
            raise SSHRotateError(
                f"Ошибка смены пароля: {real_error or f'exit code {exit_code}'}"
            )

        logger.info(f"Password rotated OK for {username}@{host}")

    except AuthenticationException:
        raise SSHRotateError(
            "Ошибка аутентификации SSH — неверные текущие учётные данные"
        )

    except NoValidConnectionsError:
        raise SSHRotateError(f"Не удалось подключиться к {host}:{port}")

    except SSHException as e:
        raise SSHRotateError(f"SSH ошибка: {e}")

    except TimeoutError:
        raise SSHRotateError(f"Таймаут подключения к {host}:{port}")

    finally:
        client.close()
