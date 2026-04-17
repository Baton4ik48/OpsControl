import pytest
from unittest.mock import Mock, patch

from app.services.credentials import (
    verify_admin_password,
    upsert_credentials,
    show_credentials,
    rotate_credentials,
    InvalidMasterPassword,
    CredentialsNotFound,
    TooManyLoginAttempts,
    RotateError,
)
from app.services.vault_client import (
    VaultAuthError,
    VaultReadError,
    VaultUnavailableError,
)
from app.services.login_throttle import TooManyAttempts

# ============================================================
# verify_admin_password
# ============================================================


@patch("app.services.credentials.get_vault_client")
@patch("app.services.credentials.throttle")
@patch("app.services.credentials.settings")
def test_verify_admin_password_success(settings, throttle, get_vault_client):
    settings.LOGIN_THROTTLE_ENABLED = True

    vault = Mock()
    get_vault_client.return_value = vault

    verify_admin_password("Admin", "pass", "1.1.1.1")

    vault.login_userpass.assert_called_once_with("admin", "pass")
    throttle.reset.assert_called_once()


@patch("app.services.credentials.get_vault_client")
@patch("app.services.credentials.throttle")
@patch("app.services.credentials.settings")
def test_verify_admin_password_username_lowercased(
    settings, _throttle, get_vault_client
):
    """username всегда передаётся в lower() в Vault"""
    settings.LOGIN_THROTTLE_ENABLED = False

    vault = Mock()
    get_vault_client.return_value = vault

    verify_admin_password("ADMIN", "pass", "ip")

    vault.login_userpass.assert_called_once_with("admin", "pass")


@patch("app.services.credentials.get_vault_client")
@patch("app.services.credentials.throttle")
@patch("app.services.credentials.settings")
def test_verify_admin_password_invalid_password(settings, throttle, get_vault_client):
    settings.LOGIN_THROTTLE_ENABLED = True

    vault = Mock()
    vault.login_userpass.side_effect = VaultAuthError()
    get_vault_client.return_value = vault

    with pytest.raises(InvalidMasterPassword):
        verify_admin_password("admin", "wrong", "1.1.1.1")

    throttle.register_fail.assert_called_once()


@patch("app.services.credentials.throttle")
@patch("app.services.credentials.settings")
def test_verify_admin_password_too_many_attempts(settings, throttle):
    settings.LOGIN_THROTTLE_ENABLED = True

    throttle.check.side_effect = TooManyAttempts()
    throttle.time_until_unblock.return_value = 42

    with pytest.raises(TooManyLoginAttempts) as exc:
        verify_admin_password("admin", "pass", "1.1.1.1")

    assert exc.value.retry_after_seconds == 42


@patch("app.services.credentials.get_vault_client")
@patch("app.services.credentials.settings")
def test_verify_admin_password_vault_unavailable(settings, get_vault_client):
    """VaultUnavailableError не перехватывается → пробрасывается наружу"""
    settings.LOGIN_THROTTLE_ENABLED = False

    vault = Mock()
    vault.login_userpass.side_effect = VaultUnavailableError("vault down")
    get_vault_client.return_value = vault

    with pytest.raises(VaultUnavailableError):
        verify_admin_password("admin", "pass", "1.1.1.1")


@patch("app.services.credentials.get_vault_client")
@patch("app.services.credentials.throttle")
@patch("app.services.credentials.settings")
def test_verify_no_throttle(get_vault_client, settings, throttle):
    """Когда throttle выключен — check/reset/register_fail не вызываются"""
    settings.LOGIN_THROTTLE_ENABLED = False

    vault = Mock()
    get_vault_client.return_value = vault

    verify_admin_password("admin", "pass", "ip")

    throttle.check.assert_not_called()
    throttle.reset.assert_not_called()
    throttle.register_fail.assert_not_called()


@patch("app.services.credentials.get_vault_client")
@patch("app.services.credentials.throttle")
@patch("app.services.credentials.settings")
def test_verify_admin_password_no_reset_when_throttle_disabled(
    settings, throttle, get_vault_client
):
    """Успешный логин без throttle → reset не вызывается"""
    settings.LOGIN_THROTTLE_ENABLED = False

    vault = Mock()
    get_vault_client.return_value = vault

    verify_admin_password("admin", "pass", "ip")

    throttle.reset.assert_not_called()


# ============================================================
# upsert_credentials
# ============================================================


@patch("app.services.credentials.upsert_vault_path")
@patch("app.services.credentials.get_vault_client")
def test_upsert_credentials_success(get_vault_client, upsert_vault_path):
    vault = Mock()
    get_vault_client.return_value = vault

    path = upsert_credentials(1, 22, "user", "pass")

    assert path == "credentials/servers/1/22"
    vault.write_kv_v2.assert_called_once_with(
        "credentials/servers/1/22",
        {"username": "user", "password": "pass"},
    )
    upsert_vault_path.assert_called_once_with(1, 22, "credentials/servers/1/22")


@patch("app.services.credentials.upsert_vault_path")
@patch("app.services.credentials.get_vault_client")
def test_upsert_credentials_vault_error(get_vault_client, upsert_vault_path):
    """Vault write упал → VaultReadError, БД не трогаем"""
    vault = Mock()
    vault.write_kv_v2.side_effect = VaultReadError()
    get_vault_client.return_value = vault

    with pytest.raises(VaultReadError):
        upsert_credentials(1, 22, "user", "pass")

    upsert_vault_path.assert_not_called()


# ============================================================
# show_credentials
# ============================================================


@patch("app.services.credentials.get_vault_path_by_server_port")
@patch("app.services.credentials.get_vault_client")
@patch("app.services.credentials.settings")
def test_show_credentials_success(settings, get_vault_client, get_path):
    settings.LOGIN_THROTTLE_ENABLED = False

    vault = Mock()
    vault.login_userpass.return_value = "user-token"
    vault.read_kv_v2.return_value = {
        "username": "user",
        "password": "pass",
        "mnemonic": "some hint",
    }
    get_vault_client.return_value = vault
    get_path.return_value = "credentials/servers/1/22"

    result = show_credentials(1, 22, "admin", "pass", "ip")

    assert result == {"username": "user", "password": "pass", "mnemonic": "some hint"}
    vault.read_kv_v2.assert_called_once_with("user-token", "credentials/servers/1/22")


@patch("app.services.credentials.get_vault_path_by_server_port")
@patch("app.services.credentials.get_vault_client")
@patch("app.services.credentials.settings")
def test_show_credentials_mnemonic_defaults_to_empty(
    settings, get_vault_client, get_path
):
    """Если в Vault нет mnemonic → возвращается пустая строка"""
    settings.LOGIN_THROTTLE_ENABLED = False

    vault = Mock()
    vault.login_userpass.return_value = "token"
    vault.read_kv_v2.return_value = {"username": "u", "password": "p"}
    get_vault_client.return_value = vault
    get_path.return_value = "credentials/servers/1/22"

    result = show_credentials(1, 22, "admin", "pass", "ip")

    assert result["mnemonic"] == ""


@patch("app.services.credentials.get_vault_path_by_server_port")
@patch("app.services.credentials.get_vault_client")
@patch("app.services.credentials.settings")
def test_show_credentials_not_found(settings, get_vault_client, get_path):
    settings.LOGIN_THROTTLE_ENABLED = False

    vault = Mock()
    vault.login_userpass.return_value = "token"
    get_vault_client.return_value = vault
    get_path.return_value = None

    with pytest.raises(CredentialsNotFound):
        show_credentials(1, 22, "admin", "pass", "ip")


@patch("app.services.credentials.get_vault_client")
@patch("app.services.credentials.settings")
def test_show_credentials_invalid_password(settings, get_vault_client):
    settings.LOGIN_THROTTLE_ENABLED = False

    vault = Mock()
    vault.login_userpass.side_effect = VaultAuthError()
    get_vault_client.return_value = vault

    with pytest.raises(InvalidMasterPassword):
        show_credentials(1, 22, "admin", "wrong", "ip")


@patch("app.services.credentials.get_vault_path_by_server_port")
@patch("app.services.credentials.get_vault_client")
@patch("app.services.credentials.settings")
def test_show_credentials_vault_read_error(settings, get_vault_client, get_path):
    """VaultReadError при чтении → CredentialsNotFound (не пробрасывается)"""
    settings.LOGIN_THROTTLE_ENABLED = False

    vault = Mock()
    vault.login_userpass.return_value = "token"
    vault.read_kv_v2.side_effect = VaultReadError()
    get_vault_client.return_value = vault
    get_path.return_value = "credentials/servers/1/22"

    with pytest.raises(CredentialsNotFound):
        show_credentials(1, 22, "admin", "pass", "ip")


@patch("app.services.credentials.throttle")
@patch("app.services.credentials.settings")
def test_show_credentials_throttle_block(settings, throttle):
    settings.LOGIN_THROTTLE_ENABLED = True

    throttle.check.side_effect = TooManyAttempts()
    throttle.time_until_unblock.return_value = 10

    with pytest.raises(TooManyLoginAttempts) as exc:
        show_credentials(1, 22, "admin", "pass", "ip")

    assert exc.value.retry_after_seconds == 10


# ============================================================
# rotate_credentials
# ============================================================


@patch("app.services.credentials.touch_credentials_updated_at")
@patch("app.services.credentials.get_vault_client")
@patch("app.services.credentials.get_vault_path_by_server_port")
@patch("app.services.credentials.verify_admin_password")
def test_rotate_success(verify, get_path, get_vault_client, touch_updated):
    vault = Mock()
    vault._get_backend_token.return_value = "backend-token"
    vault.read_kv_v2.return_value = {"username": "user"}
    get_vault_client.return_value = vault
    get_path.return_value = "credentials/servers/1/22"

    rotate_credentials(1, 22, "newpass", "admin", "mpass", "ip")

    vault.write_kv_v2.assert_called_once_with(
        "credentials/servers/1/22",
        {"username": "user", "password": "newpass", "mnemonic": ""},
    )
    touch_updated.assert_called_once_with(1, 22)


@patch("app.services.credentials.touch_credentials_updated_at")
@patch("app.services.credentials.get_vault_client")
@patch("app.services.credentials.get_vault_path_by_server_port")
@patch("app.services.credentials.verify_admin_password")
def test_rotate_success_with_mnemonic(
    _verify, get_path, get_vault_client, _touch_updated
):
    """Мнемоника сохраняется в Vault при передаче"""
    vault = Mock()
    vault._get_backend_token.return_value = "token"
    vault.read_kv_v2.return_value = {"username": "user"}
    get_vault_client.return_value = vault
    get_path.return_value = "credentials/servers/1/22"

    rotate_credentials(1, 22, "newpass", "admin", "mpass", "ip", mnemonic="hint123")

    vault.write_kv_v2.assert_called_once_with(
        "credentials/servers/1/22",
        {"username": "user", "password": "newpass", "mnemonic": "hint123"},
    )


@patch("app.services.credentials.verify_admin_password")
def test_rotate_verify_failed(verify):
    """verify_admin_password упал → rotate прерывается, исключение пробрасывается"""
    verify.side_effect = InvalidMasterPassword()

    with pytest.raises(InvalidMasterPassword):
        rotate_credentials(1, 22, "new", "admin", "mpass", "ip")


@patch("app.services.credentials.get_vault_path_by_server_port")
@patch("app.services.credentials.verify_admin_password")
def test_rotate_no_path(_verify, get_path):
    """vault_path не найден в БД → RotateError"""
    get_path.return_value = None

    with pytest.raises(RotateError):
        rotate_credentials(1, 22, "new", "admin", "mpass", "ip")


@patch("app.services.credentials.get_vault_client")
@patch("app.services.credentials.get_vault_path_by_server_port")
@patch("app.services.credentials.verify_admin_password")
def test_rotate_read_error(verify, get_path, get_vault_client):
    """VaultReadError при чтении текущих кред → RotateError"""
    vault = Mock()
    vault._get_backend_token.return_value = "token"
    vault.read_kv_v2.side_effect = VaultReadError("read fail")
    get_vault_client.return_value = vault
    get_path.return_value = "credentials/servers/1/22"

    with pytest.raises(RotateError):
        rotate_credentials(1, 22, "new", "admin", "mpass", "ip")


@patch("app.services.credentials.get_vault_client")
@patch("app.services.credentials.get_vault_path_by_server_port")
@patch("app.services.credentials.verify_admin_password")
def test_rotate_write_error(verify, get_path, get_vault_client):
    """VaultReadError при записи нового пароля → RotateError"""
    vault = Mock()
    vault._get_backend_token.return_value = "token"
    vault.read_kv_v2.return_value = {"username": "user"}
    vault.write_kv_v2.side_effect = VaultReadError("write fail")
    get_vault_client.return_value = vault
    get_path.return_value = "credentials/servers/1/22"

    with pytest.raises(RotateError):
        rotate_credentials(1, 22, "new", "admin", "mpass", "ip")


@patch("app.services.credentials.touch_credentials_updated_at")
@patch("app.services.credentials.get_vault_client")
@patch("app.services.credentials.get_vault_path_by_server_port")
@patch("app.services.credentials.verify_admin_password")
def test_rotate_touch_not_called_on_write_error(
    verify, get_path, get_vault_client, touch_updated
):
    """Если write в Vault упал → touch_credentials_updated_at не вызывается"""
    vault = Mock()
    vault._get_backend_token.return_value = "token"
    vault.read_kv_v2.return_value = {"username": "user"}
    vault.write_kv_v2.side_effect = VaultReadError()
    get_vault_client.return_value = vault
    get_path.return_value = "credentials/servers/1/22"

    with pytest.raises(RotateError):
        rotate_credentials(1, 22, "new", "admin", "mpass", "ip")

    touch_updated.assert_not_called()
