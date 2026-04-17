import pytest
from unittest.mock import Mock

from app.services.db.ports_db import (
    load_ports,
    create_port,
    update_port,
    report_port_result,
    update_vault_path,
    delete_port,
    delete_credentials,
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
        "app.services.db.ports_db._execute",
        lambda fn, retries=1: fn(conn),
    )


# ============================================
# load_ports
# ============================================


def test_load_ports_returns_dict_list(monkeypatch):
    from datetime import datetime

    t1, t2 = datetime(2024, 1, 1), datetime(2024, 1, 2)
    conn, cur = _make_conn(fetchall=[(22, t1, None), (443, None, t2)])
    _patch(monkeypatch, conn)

    result = load_ports(server_id=3)

    assert len(result) == 2
    assert result[0] == {"port": 22, "last_success": t1, "last_failure": None}
    assert result[1] == {"port": 443, "last_success": None, "last_failure": t2}

    sql, params = cur.execute.call_args[0]
    assert "ports" in sql
    assert params == (3,)


def test_load_ports_empty(monkeypatch):
    conn, cur = _make_conn(fetchall=[])
    _patch(monkeypatch, conn)

    assert load_ports(1) == []


def test_load_ports_db_unavailable(monkeypatch):
    monkeypatch.setattr(
        "app.services.db.ports_db._execute",
        lambda fn, retries=1: (_ for _ in ()).throw(ServiceUnavailableError()),
    )
    with pytest.raises(ServiceUnavailableError):
        load_ports(1)


# ============================================
# create_port
# ============================================


def test_create_port_returns_one(monkeypatch):
    conn, cur = _make_conn()
    _patch(monkeypatch, conn)

    result = create_port(server_id=2, port=8080)

    assert result == 1
    sql, params = cur.execute.call_args[0]
    assert "INSERT" in sql
    assert "ports" in sql
    assert params == (2, 8080)
    conn.commit.assert_called_once()


def test_create_port_db_unavailable(monkeypatch):
    monkeypatch.setattr(
        "app.services.db.ports_db._execute",
        lambda fn, retries=1: (_ for _ in ()).throw(ServiceUnavailableError()),
    )
    with pytest.raises(ServiceUnavailableError):
        create_port(1, 22)


# ============================================
# update_port
# ============================================


def test_update_port_same_port_returns_one_no_sql(monkeypatch):
    """Одинаковые порты → короткий выход, SQL не выполняется"""
    conn, cur = _make_conn()
    _patch(monkeypatch, conn)

    result = update_port(server_id=1, old_port=22, new_port=22)

    assert result == 1
    cur.execute.assert_not_called()
    conn.commit.assert_not_called()


def test_update_port_different_port(monkeypatch):
    """Разные порты → DELETE credentials + UPDATE port"""
    conn, cur = _make_conn(rowcount=1)
    _patch(monkeypatch, conn)

    result = update_port(server_id=1, old_port=22, new_port=2222)

    assert result == 1
    assert cur.execute.call_count == 2

    first_sql = cur.execute.call_args_list[0][0][0]
    second_sql = cur.execute.call_args_list[1][0][0]
    assert "DELETE" in first_sql
    assert "credentials" in first_sql
    assert "UPDATE" in second_sql
    assert "ports" in second_sql
    conn.commit.assert_called_once()


def test_update_port_db_unavailable(monkeypatch):
    monkeypatch.setattr(
        "app.services.db.ports_db._execute",
        lambda fn, retries=1: (_ for _ in ()).throw(ServiceUnavailableError()),
    )
    with pytest.raises(ServiceUnavailableError):
        update_port(1, 22, 2222)


# ============================================
# report_port_result
# ============================================


def test_report_port_result_ok_updates_last_success(monkeypatch):
    conn, cur = _make_conn(rowcount=1)
    _patch(monkeypatch, conn)

    result = report_port_result(server_id=1, port=22, ok=True)

    assert result == 1
    sql = cur.execute.call_args[0][0]
    assert "last_success" in sql
    assert "last_failure" not in sql


def test_report_port_result_fail_updates_last_failure(monkeypatch):
    conn, cur = _make_conn(rowcount=1)
    _patch(monkeypatch, conn)

    result = report_port_result(server_id=1, port=22, ok=False)

    assert result == 1
    sql = cur.execute.call_args[0][0]
    assert "last_failure" in sql
    assert "last_success" not in sql


def test_report_port_result_db_unavailable(monkeypatch):
    monkeypatch.setattr(
        "app.services.db.ports_db._execute",
        lambda fn, retries=1: (_ for _ in ()).throw(ServiceUnavailableError()),
    )
    with pytest.raises(ServiceUnavailableError):
        report_port_result(1, 22, True)


# ============================================
# update_vault_path
# ============================================


def test_update_vault_path_empty_deletes_credentials(monkeypatch):
    """Пустой путь → DELETE credentials"""
    conn, cur = _make_conn()
    _patch(monkeypatch, conn)

    result = update_vault_path(server_id=1, port=22, new_path="")

    assert result == 1
    sql = cur.execute.call_args[0][0]
    assert "DELETE" in sql
    assert "credentials" in sql


def test_update_vault_path_whitespace_deletes_credentials(monkeypatch):
    """Строка из пробелов → тоже DELETE"""
    conn, cur = _make_conn()
    _patch(monkeypatch, conn)

    result = update_vault_path(server_id=1, port=22, new_path="   ")

    assert result == 1
    sql = cur.execute.call_args[0][0]
    assert "DELETE" in sql


def test_update_vault_path_nonempty_upserts(monkeypatch):
    """Непустой путь → UPSERT"""
    conn, cur = _make_conn()
    _patch(monkeypatch, conn)

    result = update_vault_path(
        server_id=1, port=22, new_path="credentials/servers/1/22"
    )

    assert result == 1
    sql, params = cur.execute.call_args[0]
    assert "INSERT" in sql
    assert "ON CONFLICT" in sql
    assert params == (1, 22, "credentials/servers/1/22")


def test_update_vault_path_db_unavailable(monkeypatch):
    monkeypatch.setattr(
        "app.services.db.ports_db._execute",
        lambda fn, retries=1: (_ for _ in ()).throw(ServiceUnavailableError()),
    )
    with pytest.raises(ServiceUnavailableError):
        update_vault_path(1, 22, "path")


# ============================================
# delete_port
# ============================================


def test_delete_port_returns_rowcount(monkeypatch):
    conn, cur = _make_conn(rowcount=1)
    _patch(monkeypatch, conn)

    result = delete_port(server_id=1, port=22)

    assert result == 1
    sql, params = cur.execute.call_args[0]
    assert "DELETE" in sql
    assert "ports" in sql
    assert params == (1, 22)


def test_delete_port_not_found(monkeypatch):
    conn, cur = _make_conn(rowcount=0)
    _patch(monkeypatch, conn)

    assert delete_port(1, 9999) == 0


def test_delete_port_db_unavailable(monkeypatch):
    monkeypatch.setattr(
        "app.services.db.ports_db._execute",
        lambda fn, retries=1: (_ for _ in ()).throw(ServiceUnavailableError()),
    )
    with pytest.raises(ServiceUnavailableError):
        delete_port(1, 22)


# ============================================
# delete_credentials
# ============================================


def test_delete_credentials_returns_rowcount(monkeypatch):
    conn, cur = _make_conn(rowcount=1)
    _patch(monkeypatch, conn)

    result = delete_credentials(server_id=1, port=22)

    assert result == 1
    sql, params = cur.execute.call_args[0]
    assert "DELETE" in sql
    assert "credentials" in sql
    assert params == (1, 22)


def test_delete_credentials_not_found(monkeypatch):
    conn, cur = _make_conn(rowcount=0)
    _patch(monkeypatch, conn)

    assert delete_credentials(1, 9999) == 0
