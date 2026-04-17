import asyncio
import pytest
from unittest.mock import MagicMock, patch

from app.services.vault_renewer import vault_renew_loop
from app.services.vault_client import (
    VaultSealedError,
    VaultUnavailableError,
    VaultAuthError,
)


def _make_vault(renew_result=True):
    mock = MagicMock()
    mock._renew_token.return_value = renew_result
    mock._backend_token = "token"
    return mock


async def _run_one_tick(mock_vault, interval=1):
    """Запускает loop ровно один тик, затем отменяет через CancelledError."""
    sleep_calls = 0

    async def fake_sleep(n):
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls > 1:
            raise asyncio.CancelledError()

    with patch(
        "app.services.vault_client.get_vault_client", return_value=mock_vault
    ), patch("asyncio.sleep", side_effect=fake_sleep):
        with pytest.raises(asyncio.CancelledError):
            await vault_renew_loop(interval=interval)


@pytest.mark.asyncio
async def test_renew_loop_successful_renew():
    """renew успешен → re-login не вызывается"""
    vault = _make_vault(renew_result=True)

    await _run_one_tick(vault)

    vault._renew_token.assert_called_once()
    vault._get_backend_token.assert_not_called()


@pytest.mark.asyncio
async def test_renew_loop_relogin_on_renew_failure():
    """renew вернул False → сбрасывает токен и вызывает _get_backend_token"""
    vault = _make_vault(renew_result=False)

    await _run_one_tick(vault)

    vault._renew_token.assert_called_once()
    assert vault._backend_token is None
    vault._get_backend_token.assert_called_once()


@pytest.mark.asyncio
async def test_renew_loop_vault_sealed_does_not_crash():
    """VaultSealedError → логируется, цикл продолжается (не падает)"""
    vault = _make_vault()
    vault._renew_token.side_effect = VaultSealedError("sealed")

    # Ожидаем CancelledError (второй тик), а не VaultSealedError
    await _run_one_tick(vault)


@pytest.mark.asyncio
async def test_renew_loop_vault_unavailable_does_not_crash():
    """VaultUnavailableError → логируется, цикл продолжается"""
    vault = _make_vault()
    vault._renew_token.side_effect = VaultUnavailableError("offline")

    await _run_one_tick(vault)


@pytest.mark.asyncio
async def test_renew_loop_auth_error_does_not_crash():
    """VaultAuthError → логируется с подсказкой, цикл продолжается"""
    vault = _make_vault()
    vault._renew_token.side_effect = VaultAuthError("bad creds")

    await _run_one_tick(vault)


@pytest.mark.asyncio
async def test_renew_loop_unexpected_exception_does_not_crash():
    """Любое неожиданное исключение → логируется, цикл не падает"""
    vault = _make_vault()
    vault._renew_token.side_effect = RuntimeError("unexpected")

    await _run_one_tick(vault)
