import pytest
from unittest.mock import Mock

from app.services.db.servers_db import (
    load_servers,
    create_server,
    update_server,
    delete_server,
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


def _patch(monkeypatch, conn):
    monkeypatch.setattr(
        "app.services.db.servers_db._execute",
        lambda fn, retries=1: fn(conn),
    )


def test_load_servers_returns_rows(monkeypatch):
    rows = [(1, "srv1", "10.0.0.1", "linux"), (2, "srv2", "10.0.0.2", "windows")]
    conn, cur = _make_conn(fetchall=rows)
    _patch(monkeypatch, conn)

    result = load_servers(branch_id=7)

    assert result == rows
    sql, params = cur.execute.call_args[0]
    assert "SELECT" in sql
    assert "servers" in sql
    assert params == (7,)


def test_load_servers_empty(monkeypatch):
    conn, cur = _make_conn(fetchall=[])
    _patch(monkeypatch, conn)

    assert load_servers(branch_id=99) == []


def test_load_servers_db_unavailable(monkeypatch):
    monkeypatch.setattr(
        "app.services.db.servers_db._execute",
        lambda fn, retries=1: (_ for _ in ()).throw(ServiceUnavailableError()),
    )
    with pytest.raises(ServiceUnavailableError):
        load_servers(1)


def test_create_server_returns_new_id(monkeypatch):
    conn, cur = _make_conn(fetchone=(17,))
    _patch(monkeypatch, conn)

    result = create_server(
        branch_id=2, name="db01", ip="192.168.1.5", device_type="linux"
    )

    assert result == 17
    sql, params = cur.execute.call_args[0]
    assert "INSERT" in sql
    assert "servers" in sql
    assert params == (2, "db01", "192.168.1.5", "linux")
    conn.commit.assert_called_once()


def test_create_server_default_device_type(monkeypatch):
    conn, cur = _make_conn(fetchone=(1,))
    _patch(monkeypatch, conn)

    create_server(branch_id=1, name="x", ip="1.2.3.4")

    _, params = cur.execute.call_args[0]
    assert params[3] == "linux"


def test_create_server_db_unavailable(monkeypatch):
    monkeypatch.setattr(
        "app.services.db.servers_db._execute",
        lambda fn, retries=1: (_ for _ in ()).throw(ServiceUnavailableError()),
    )
    with pytest.raises(ServiceUnavailableError):
        create_server(1, "x", "1.1.1.1")


def test_update_server_returns_rowcount(monkeypatch):
    conn, cur = _make_conn(rowcount=1)
    _patch(monkeypatch, conn)

    result = update_server(
        server_id=5, name="new", ip="10.10.10.1", device_type="cisco"
    )

    assert result == 1
    sql, params = cur.execute.call_args[0]
    assert "UPDATE" in sql
    assert "servers" in sql
    assert params == ("new", "10.10.10.1", "cisco", 5)
    conn.commit.assert_called_once()


def test_update_server_not_found(monkeypatch):
    conn, cur = _make_conn(rowcount=0)
    _patch(monkeypatch, conn)

    assert update_server(999, "x", "1.1.1.1") == 0


def test_update_server_db_unavailable(monkeypatch):
    monkeypatch.setattr(
        "app.services.db.servers_db._execute",
        lambda fn, retries=1: (_ for _ in ()).throw(ServiceUnavailableError()),
    )
    with pytest.raises(ServiceUnavailableError):
        update_server(1, "x", "1.1.1.1")


def test_delete_server_returns_rowcount(monkeypatch):
    conn, cur = _make_conn(rowcount=1)
    _patch(monkeypatch, conn)

    result = delete_server(server_id=8)

    assert result == 1
    sql, params = cur.execute.call_args[0]
    assert "DELETE" in sql
    assert "servers" in sql
    assert params == (8,)
    conn.commit.assert_called_once()


def test_delete_server_not_found(monkeypatch):
    conn, cur = _make_conn(rowcount=0)
    _patch(monkeypatch, conn)

    assert delete_server(999) == 0


def test_delete_server_db_unavailable(monkeypatch):
    monkeypatch.setattr(
        "app.services.db.servers_db._execute",
        lambda fn, retries=1: (_ for _ in ()).throw(ServiceUnavailableError()),
    )
    with pytest.raises(ServiceUnavailableError):
        delete_server(1)
