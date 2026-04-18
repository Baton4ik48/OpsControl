import pytest
from unittest.mock import Mock

from app.services.db.credentials_db import (
    get_vault_path_by_server_port,
    get_credentials_username,
    touch_credentials_updated_at,
    upsert_vault_path,
)
from app.services.db.pool_db import ServiceUnavailableError


def _make_conn(fetchone=None, fetchall=None, rowcount=1):
    cur = Mock()
    cur.fetchone.return_value = fetchone
    cur.fetchall.return_value = fetchall or []
    cur.rowcount = rowcount
    conn = Mock()
    conn.cursor.return_value = cur
    return conn, cur


def _patch(monkeypatch, conn, module_fn="app.services.db.credentials_db._execute"):
    monkeypatch.setattr(module_fn, lambda fn, retries=1: fn(conn))


# ============================================
# get_vault_path_by_server_port
# ============================================


def test_get_vault_path_found(monkeypatch):
    conn, cur = _make_conn(fetchone=("credentials/servers/1/22",))
    _patch(monkeypatch, conn)

    result = get_vault_path_by_server_port(server_id=1, port=22)

    assert result == "credentials/servers/1/22"
    sql, params = cur.execute.call_args[0]
    assert "credentials" in sql
    assert params == (1, 22)


def test_get_vault_path_not_found(monkeypatch):
    conn, cur = _make_conn(fetchone=None)
    _patch(monkeypatch, conn)

    result = get_vault_path_by_server_port(server_id=1, port=9999)

    assert result is None


def test_get_vault_path_db_unavailable(monkeypatch):
    monkeypatch.setattr(
        "app.services.db.credentials_db._execute",
        lambda fn, retries=1: (_ for _ in ()).throw(ServiceUnavailableError()),
    )
    with pytest.raises(ServiceUnavailableError):
        get_vault_path_by_server_port(1, 22)


# ============================================
# get_credentials_username
# ============================================


def test_get_credentials_username_found(monkeypatch):
    """Функция возвращает vault_path (не username) — тестируем реальное поведение кода"""
    conn, cur = _make_conn(fetchone=("credentials/servers/2/443",))
    _patch(monkeypatch, conn)

    result = get_credentials_username(server_id=2, port=443)

    assert result == "credentials/servers/2/443"
    sql, params = cur.execute.call_args[0]
    assert "credentials" in sql
    assert params == (2, 443)


def test_get_credentials_username_not_found(monkeypatch):
    conn, cur = _make_conn(fetchone=None)
    _patch(monkeypatch, conn)

    assert get_credentials_username(server_id=1, port=9999) is None


def test_get_credentials_username_db_unavailable(monkeypatch):
    monkeypatch.setattr(
        "app.services.db.credentials_db._execute",
        lambda fn, retries=1: (_ for _ in ()).throw(ServiceUnavailableError()),
    )
    with pytest.raises(ServiceUnavailableError):
        get_credentials_username(1, 22)


# ============================================
# touch_credentials_updated_at
# ============================================


def test_touch_credentials_updated_at_executes_update(monkeypatch):
    conn, cur = _make_conn()
    _patch(monkeypatch, conn)

    result = touch_credentials_updated_at(server_id=3, port=22)

    assert result is None
    sql, params = cur.execute.call_args[0]
    assert "UPDATE" in sql
    assert "credentials" in sql
    assert "updated_at" in sql
    assert params == (3, 22)
    conn.commit.assert_called_once()


def test_touch_credentials_updated_at_db_unavailable(monkeypatch):
    monkeypatch.setattr(
        "app.services.db.credentials_db._execute",
        lambda fn, retries=1: (_ for _ in ()).throw(ServiceUnavailableError()),
    )
    with pytest.raises(ServiceUnavailableError):
        touch_credentials_updated_at(1, 22)


# ============================================
# upsert_vault_path
# ============================================


def test_upsert_vault_path_inserts_or_updates(monkeypatch):
    conn, cur = _make_conn()
    _patch(monkeypatch, conn)

    result = upsert_vault_path(
        server_id=1, port=22, vault_path="credentials/servers/1/22"
    )

    assert result is None
    sql, params = cur.execute.call_args[0]
    assert "INSERT" in sql
    assert "ON CONFLICT" in sql
    assert "credentials" in sql
    assert params == (1, 22, "credentials/servers/1/22")
    conn.commit.assert_called_once()


def test_upsert_vault_path_db_unavailable(monkeypatch):
    monkeypatch.setattr(
        "app.services.db.credentials_db._execute",
        lambda fn, retries=1: (_ for _ in ()).throw(ServiceUnavailableError()),
    )
    with pytest.raises(ServiceUnavailableError):
        upsert_vault_path(1, 22, "path")
