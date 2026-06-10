import pytest
from unittest.mock import Mock
from psycopg2 import OperationalError, InterfaceError
from psycopg2 import errors as pg_errors

import app.services.db.pool_db as pool_module
from app.services.db.pool_db import (
    init_pool,
    close_pool,
    _execute,
    ServiceUnavailableError,
)


@pytest.fixture(autouse=True)
def reset_pool():
    original = pool_module.pool
    yield
    pool_module.pool = original


def test_init_pool_success(monkeypatch):
    """Успешная инициализация → True, pool установлен"""
    mock_creds = Mock(host="localhost", port=5432, dbname="db", user="u", password="p")
    mock_pool = Mock()

    monkeypatch.setattr(
        "app.services.db.pool_db.get_db_credentials", lambda: mock_creds
    )
    monkeypatch.setattr("app.services.db.pool_db.settings.POSTGRES_CONNECT_TIMEOUT", 5)
    monkeypatch.setattr("app.services.db.pool_db.settings.POSTGRES_QUERY_TIMEOUT", 30)
    monkeypatch.setattr(
        "app.services.db.pool_db.SimpleConnectionPool", lambda *a, **kw: mock_pool
    )
    monkeypatch.setattr("app.services.db.pool_db.time.sleep", lambda n: None)

    result = init_pool()

    assert result is True
    assert pool_module.pool is mock_pool


def test_init_pool_credentials_error(monkeypatch):
    """get_db_credentials падает → False, pool=None"""
    monkeypatch.setattr(
        "app.services.db.pool_db.get_db_credentials",
        Mock(side_effect=Exception("vault down")),
    )

    result = init_pool()

    assert result is False
    assert pool_module.pool is None


def test_init_pool_all_retries_fail(monkeypatch):
    """OperationalError на всех попытках → False, pool=None"""
    mock_creds = Mock(host="localhost", port=5432, dbname="db", user="u", password="p")

    monkeypatch.setattr(
        "app.services.db.pool_db.get_db_credentials", lambda: mock_creds
    )
    monkeypatch.setattr("app.services.db.pool_db.settings.POSTGRES_CONNECT_TIMEOUT", 5)
    monkeypatch.setattr("app.services.db.pool_db.settings.POSTGRES_QUERY_TIMEOUT", 30)
    monkeypatch.setattr(
        "app.services.db.pool_db.SimpleConnectionPool",
        Mock(side_effect=OperationalError("refused")),
    )
    monkeypatch.setattr("app.services.db.pool_db.time.sleep", lambda n: None)

    result = init_pool(retries=2)

    assert result is False
    assert pool_module.pool is None


def test_init_pool_retry_then_success(monkeypatch):
    """Первая попытка падает, вторая успешна → True"""
    mock_creds = Mock(host="localhost", port=5432, dbname="db", user="u", password="p")
    mock_pool = Mock()

    attempts = {"n": 0}

    def fake_pool(*a, **kw):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise OperationalError("refused")
        return mock_pool

    monkeypatch.setattr(
        "app.services.db.pool_db.get_db_credentials", lambda: mock_creds
    )
    monkeypatch.setattr("app.services.db.pool_db.settings.POSTGRES_CONNECT_TIMEOUT", 5)
    monkeypatch.setattr("app.services.db.pool_db.settings.POSTGRES_QUERY_TIMEOUT", 30)
    monkeypatch.setattr("app.services.db.pool_db.SimpleConnectionPool", fake_pool)
    monkeypatch.setattr("app.services.db.pool_db.time.sleep", lambda n: None)

    result = init_pool(retries=3)

    assert result is True
    assert pool_module.pool is mock_pool
    assert attempts["n"] == 2


def test_close_pool_when_pool_exists(monkeypatch):
    mock_pool = Mock()
    monkeypatch.setattr(pool_module, "pool", mock_pool)

    close_pool()

    mock_pool.closeall.assert_called_once()
    assert pool_module.pool is None


def test_close_pool_when_pool_is_none(monkeypatch):
    monkeypatch.setattr(pool_module, "pool", None)

    close_pool()


def test_execute_success(monkeypatch):
    """pool есть → fn вызывается, результат возвращается, putconn в finally"""
    mock_conn = Mock()
    mock_pool = Mock()
    mock_pool.getconn.return_value = mock_conn
    monkeypatch.setattr(pool_module, "pool", mock_pool)

    result = _execute(lambda conn: "ok")

    assert result == "ok"
    mock_pool.putconn.assert_called_once_with(mock_conn)


def test_execute_pool_none_init_fails(monkeypatch):
    """pool=None, init_pool не восстанавливает → ServiceUnavailableError"""
    monkeypatch.setattr(pool_module, "pool", None)
    monkeypatch.setattr(pool_module, "init_pool", lambda: None)

    with pytest.raises(ServiceUnavailableError):
        _execute(lambda conn: "ok")


def test_execute_pool_none_init_succeeds(monkeypatch):
    """pool=None → init_pool устанавливает pool → fn вызывается"""
    mock_conn = Mock()
    mock_pool = Mock()
    mock_pool.getconn.return_value = mock_conn

    def fake_init():
        pool_module.pool = mock_pool

    monkeypatch.setattr(pool_module, "pool", None)
    monkeypatch.setattr(pool_module, "init_pool", fake_init)

    result = _execute(lambda conn: "restored")

    assert result == "restored"


def test_execute_reraises_service_unavailable(monkeypatch):
    """fn поднимает ServiceUnavailableError → пробрасывается напрямую"""
    mock_conn = Mock()
    mock_pool = Mock()
    mock_pool.getconn.return_value = mock_conn
    monkeypatch.setattr(pool_module, "pool", mock_pool)

    with pytest.raises(ServiceUnavailableError):
        _execute(lambda conn: (_ for _ in ()).throw(ServiceUnavailableError("fail")))


def test_execute_undefined_table_raises_service_unavailable(monkeypatch):
    """UndefinedTable → ServiceUnavailableError('не инициализирована')"""
    mock_conn = Mock()
    mock_pool = Mock()
    mock_pool.getconn.return_value = mock_conn
    monkeypatch.setattr(pool_module, "pool", mock_pool)

    err = pg_errors.UndefinedTable("no such table")

    with pytest.raises(ServiceUnavailableError, match="не инициализирована"):
        _execute(lambda conn: (_ for _ in ()).throw(err))


def test_execute_operational_error_exhausted(monkeypatch):
    """OperationalError на каждой попытке → ServiceUnavailableError после retries"""
    mock_pool = Mock()
    mock_pool.getconn.side_effect = OperationalError("refused")
    monkeypatch.setattr(pool_module, "pool", mock_pool)
    monkeypatch.setattr(pool_module, "close_pool", lambda: None)
    monkeypatch.setattr(pool_module, "init_pool", lambda: None)

    with pytest.raises(ServiceUnavailableError):
        _execute(lambda conn: "ok", retries=1)


def test_execute_interface_error_exhausted(monkeypatch):
    """InterfaceError → ServiceUnavailableError после retries=0"""
    mock_pool = Mock()
    mock_pool.getconn.side_effect = InterfaceError("closed")
    monkeypatch.setattr(pool_module, "pool", mock_pool)
    monkeypatch.setattr(pool_module, "close_pool", lambda: None)
    monkeypatch.setattr(pool_module, "init_pool", lambda: None)

    with pytest.raises(ServiceUnavailableError):
        _execute(lambda conn: "ok", retries=0)


def test_execute_putconn_called_even_on_fn_exception(monkeypatch):
    """Исключение в fn → finally всё равно вызывает putconn"""
    mock_conn = Mock()
    mock_pool = Mock()
    mock_pool.getconn.return_value = mock_conn
    monkeypatch.setattr(pool_module, "pool", mock_pool)

    with pytest.raises(ServiceUnavailableError):
        _execute(lambda conn: (_ for _ in ()).throw(ServiceUnavailableError("x")))

    mock_pool.putconn.assert_called_once_with(mock_conn)
