import pytest
import socket
from unittest.mock import Mock, patch

from app.services.ssh_rotate import (
    _sh_escape,
    rotate_linux_password,
    SSHRotateError,
)
from paramiko.ssh_exception import AuthenticationException

# ============================================
# _sh_escape
# ============================================


@pytest.mark.parametrize(
    "value",
    [
        "simple",
        "abc123",
    ],
)
def test_sh_escape_simple(value):
    assert _sh_escape(value) == value


@pytest.mark.parametrize(
    "value",
    [
        "with space",
        "a'b",
        'a"b',
        "a;b",
        "a$HOME",
        "a&b",
    ],
)
def test_sh_escape_special_chars(value):
    escaped = _sh_escape(value)
    assert escaped.startswith("'")
    assert escaped.endswith("'")


def test_sh_escape_empty():
    assert _sh_escape("") == "''"


# ============================================
# helpers
# ============================================


def _mock_ssh_success(exit_code=0, output=""):
    stdout = Mock()
    stdout.read.return_value = output.encode()
    stdout.channel.recv_exit_status.return_value = exit_code

    stdin = Mock()
    stdin.channel.shutdown_write = Mock()

    return stdin, stdout, None


# ============================================
# rotate_linux_password
# ============================================


def test_rotate_success():
    with patch("app.services.ssh_rotate.paramiko.SSHClient") as MockSSH:
        client = MockSSH.return_value
        client.exec_command.return_value = _mock_ssh_success(0, "")

        rotate_linux_password("1.1.1.1", "user", "old", "new")

        client.connect.assert_called_once()
        assert client.exec_command.called
        client.close.assert_called_once()


def test_rotate_auth_error():
    with patch("app.services.ssh_rotate.paramiko.SSHClient") as MockSSH:
        client = MockSSH.return_value
        client.connect.side_effect = AuthenticationException()

        with pytest.raises(SSHRotateError):
            rotate_linux_password("h", "u", "p", "n")

        client.close.assert_called_once()


def test_rotate_exec_fail():
    with patch("app.services.ssh_rotate.paramiko.SSHClient") as MockSSH:
        client = MockSSH.return_value
        client.exec_command.return_value = _mock_ssh_success(
            exit_code=1, output="some error"
        )

        with pytest.raises(SSHRotateError) as exc:
            rotate_linux_password("h", "u", "p", "n")

        assert "Ошибка смены пароля" in str(exc.value)
        client.close.assert_called_once()


def test_rotate_timeout():
    with patch("app.services.ssh_rotate.paramiko.SSHClient") as MockSSH:
        client = MockSSH.return_value
        client.connect.side_effect = socket.timeout("Connection timed out")

        with pytest.raises(SSHRotateError) as exc:
            rotate_linux_password("h", "u", "p", "n")

        assert "Таймаут" in str(exc.value)
        client.close.assert_called_once()


def test_rotate_no_valid_connection():
    """NoValidConnectionsError → SSHRotateError"""
    from paramiko.ssh_exception import NoValidConnectionsError

    with patch("app.services.ssh_rotate.paramiko.SSHClient") as MockSSH:
        client = MockSSH.return_value
        client.connect.side_effect = NoValidConnectionsError({("h", 22): Exception()})

        with pytest.raises(SSHRotateError):
            rotate_linux_password("h", "u", "p", "n")

        client.close.assert_called_once()


def test_rotate_ssh_exception():
    """SSHException (общая SSH-ошибка) → SSHRotateError"""
    from paramiko.ssh_exception import SSHException

    with patch("app.services.ssh_rotate.paramiko.SSHClient") as MockSSH:
        client = MockSSH.return_value
        client.connect.side_effect = SSHException("channel closed")

        with pytest.raises(SSHRotateError):
            rotate_linux_password("h", "u", "p", "n")

        client.close.assert_called_once()


def test_rotate_command_contains_escaped_values():
    with patch("app.services.ssh_rotate.paramiko.SSHClient") as MockSSH:
        client = MockSSH.return_value
        client.exec_command.return_value = _mock_ssh_success()

        rotate_linux_password(
            host="1.1.1.1",
            username="user name",
            current_password="old pass",
            new_password="new$pass",
        )

        args, _ = client.exec_command.call_args
        command = args[0]

        assert "'user name'" in command
        assert "'old pass'" in command
        assert "'new$pass'" in command

        client.close.assert_called_once()
