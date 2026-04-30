import pytest
from unittest.mock import Mock

from app.services.db.credentials_db import (
    get_vault_path_by_server_port,
    get_credentials_username,
    touch_credentials_updated_at,
    upsert_vault_path,
    get_all_credentials_with_server_info,
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


# ============================================
# get_all_credentials_with_server_info
# ============================================

from datetime import datetime


def _make_conn_fetchall(rows):
    cur = Mock()
    cur.fetchall.return_value = rows
    conn = Mock()
    conn.cursor.return_value = cur
    return conn, cur


def test_get_all_credentials_with_server_info_returns_all(monkeypatch):
    ts = datetime(2024, 1, 15, 10, 0, 0)
    rows = [
        ("Москва", "server-01", "10.0.0.1", 22, "credentials/servers/1/22", ts),
        ("Москва", "server-01", "10.0.0.1", 443, "credentials/servers/1/443", ts),
        ("Питер", "router-01", "10.0.1.1", 22, "credentials/servers/2/22", None),
    ]
    conn, cur = _make_conn_fetchall(rows)
    monkeypatch.setattr(
        "app.services.db.credentials_db._execute", lambda fn, retries=1: fn(conn)
    )

    result = get_all_credentials_with_server_info()

    assert len(result) == 3
    assert result[0] == {
        "branch": "Москва",
        "server_name": "server-01",
        "ip": "10.0.0.1",
        "port": 22,
        "vault_path": "credentials/servers/1/22",
        "updated_at": ts.isoformat(),
    }
    assert result[2]["updated_at"] is None
    sql = cur.execute.call_args[0][0]
    assert "JOIN servers" in sql
    assert "JOIN branches" in sql
    assert "ORDER BY" in sql


def test_get_all_credentials_with_server_info_empty(monkeypatch):
    conn, _ = _make_conn_fetchall([])
    monkeypatch.setattr(
        "app.services.db.credentials_db._execute", lambda fn, retries=1: fn(conn)
    )

    result = get_all_credentials_with_server_info()

    assert result == []


def test_get_all_credentials_with_server_info_db_unavailable(monkeypatch):
    monkeypatch.setattr(
        "app.services.db.credentials_db._execute",
        lambda fn, retries=1: (_ for _ in ()).throw(ServiceUnavailableError()),
    )
    with pytest.raises(ServiceUnavailableError):
        get_all_credentials_with_server_info()
