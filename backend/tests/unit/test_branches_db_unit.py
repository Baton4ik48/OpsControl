import pytest
from unittest.mock import Mock

from app.services.db.branches_db import (
    load_branches,
    create_branch,
    update_branch,
    delete_branch,
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
        "app.services.db.branches_db._execute",
        lambda fn, retries=1: fn(conn),
    )


# ============================================
# load_branches
# ============================================


def test_load_branches_returns_rows(monkeypatch):
    rows = [(1, "Alpha"), (2, "Beta")]
    conn, cur = _make_conn(fetchall=rows)
    _patch(monkeypatch, conn)

    result = load_branches()

    assert result == rows
    sql = cur.execute.call_args[0][0]
    assert "SELECT" in sql
    assert "branches" in sql


def test_load_branches_empty(monkeypatch):
    conn, cur = _make_conn(fetchall=[])
    _patch(monkeypatch, conn)

    assert load_branches() == []


def test_load_branches_db_unavailable(monkeypatch):
    monkeypatch.setattr(
        "app.services.db.branches_db._execute",
        lambda fn, retries=1: (_ for _ in ()).throw(ServiceUnavailableError()),
    )
    with pytest.raises(ServiceUnavailableError):
        load_branches()


# ============================================
# create_branch
# ============================================


def test_create_branch_returns_new_id(monkeypatch):
    conn, cur = _make_conn(fetchone=(42,))
    _patch(monkeypatch, conn)

    result = create_branch("NewBranch")

    assert result == 42
    sql, params = cur.execute.call_args[0]
    assert "INSERT" in sql
    assert "branches" in sql
    assert params == ("NewBranch",)
    conn.commit.assert_called_once()


def test_create_branch_db_unavailable(monkeypatch):
    monkeypatch.setattr(
        "app.services.db.branches_db._execute",
        lambda fn, retries=1: (_ for _ in ()).throw(ServiceUnavailableError()),
    )
    with pytest.raises(ServiceUnavailableError):
        create_branch("X")


# ============================================
# update_branch
# ============================================


def test_update_branch_returns_rowcount(monkeypatch):
    conn, cur = _make_conn(rowcount=1)
    _patch(monkeypatch, conn)

    result = update_branch(5, "Renamed")

    assert result == 1
    sql, params = cur.execute.call_args[0]
    assert "UPDATE" in sql
    assert "branches" in sql
    assert params == ("Renamed", 5)
    conn.commit.assert_called_once()


def test_update_branch_not_found(monkeypatch):
    conn, cur = _make_conn(rowcount=0)
    _patch(monkeypatch, conn)

    assert update_branch(999, "X") == 0


def test_update_branch_db_unavailable(monkeypatch):
    monkeypatch.setattr(
        "app.services.db.branches_db._execute",
        lambda fn, retries=1: (_ for _ in ()).throw(ServiceUnavailableError()),
    )
    with pytest.raises(ServiceUnavailableError):
        update_branch(1, "X")


# ============================================
# delete_branch
# ============================================


def test_delete_branch_returns_rowcount(monkeypatch):
    conn, cur = _make_conn(rowcount=1)
    _patch(monkeypatch, conn)

    result = delete_branch(3)

    assert result == 1
    sql, params = cur.execute.call_args[0]
    assert "DELETE" in sql
    assert "branches" in sql
    assert params == (3,)
    conn.commit.assert_called_once()


def test_delete_branch_not_found(monkeypatch):
    conn, cur = _make_conn(rowcount=0)
    _patch(monkeypatch, conn)

    assert delete_branch(999) == 0


def test_delete_branch_db_unavailable(monkeypatch):
    monkeypatch.setattr(
        "app.services.db.branches_db._execute",
        lambda fn, retries=1: (_ for _ in ()).throw(ServiceUnavailableError()),
    )
    with pytest.raises(ServiceUnavailableError):
        delete_branch(1)
