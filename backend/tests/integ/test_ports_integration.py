import pytest

from app.services.db.branches_db import create_branch, delete_branch
from app.services.db.servers_db import create_server, delete_server
from app.services.db.ports_db import (
    load_ports,
    create_port,
    update_port,
    update_vault_path,
    report_port_result,
    delete_port,
    delete_credentials,
)
from app.services.db.credentials_db import get_vault_path_by_server_port


@pytest.fixture(scope="module")
def server_id():
    branch_id = create_branch("integ-ports-branch")
    srv_id = create_server(branch_id, "integ-ports-srv", "10.1.0.1", "linux")
    yield srv_id
    delete_server(srv_id)
    delete_branch(branch_id)


@pytest.fixture
def port(server_id):
    create_port(server_id, 2222)
    yield 2222
    delete_port(server_id, 2222)


@pytest.mark.integration
def test_load_ports_empty(server_id):
    result = load_ports(server_id)
    assert result == []


@pytest.mark.integration
def test_load_ports_returns_created(server_id, port):
    result = load_ports(server_id)
    ports = [r["port"] for r in result]
    assert 2222 in ports


@pytest.mark.integration
def test_load_ports_row_structure(server_id, port):
    result = load_ports(server_id)
    row = next(r for r in result if r["port"] == 2222)
    assert "last_success" in row
    assert "last_failure" in row


@pytest.mark.integration
def test_create_port(server_id):
    result = create_port(server_id, 3333)
    assert result == 1
    delete_port(server_id, 3333)


@pytest.mark.integration
def test_update_port_same_port(server_id, port):
    affected = update_port(server_id, 2222, 2222)
    assert affected == 1


@pytest.mark.integration
def test_update_port_different_port(server_id):
    create_port(server_id, 4444)
    affected = update_port(server_id, 4444, 4445)
    assert affected == 1

    ports = [r["port"] for r in load_ports(server_id)]
    assert 4445 in ports
    assert 4444 not in ports

    delete_port(server_id, 4445)


@pytest.mark.integration
def test_update_port_migrates_credentials(server_id):
    """Credentials (vault_path) must migrate to new_port, not be deleted."""
    create_port(server_id, 6660)
    update_vault_path(server_id, 6660, "credentials/servers/test/6660")

    update_port(server_id, 6660, 6661)

    path = get_vault_path_by_server_port(server_id, 6661)
    assert path == "credentials/servers/test/6660"

    old_path = get_vault_path_by_server_port(server_id, 6660)
    assert old_path is None

    delete_port(server_id, 6661)


@pytest.mark.integration
def test_update_port_same_port_keeps_credentials(server_id, port):
    """No-op update must not touch credentials."""
    update_vault_path(server_id, 2222, "credentials/servers/test/2222")

    affected = update_port(server_id, 2222, 2222)
    assert affected == 1

    path = get_vault_path_by_server_port(server_id, 2222)
    assert path == "credentials/servers/test/2222"

    delete_credentials(server_id, 2222)


@pytest.mark.integration
def test_update_port_conflict_preserves_credentials(server_id):
    """When new_port already exists, exception is raised and old credentials survive."""
    import psycopg2

    create_port(server_id, 7770)
    create_port(server_id, 7771)
    update_vault_path(server_id, 7770, "credentials/servers/test/7770")

    with pytest.raises(psycopg2.Error):
        update_port(server_id, 7770, 7771)

    path = get_vault_path_by_server_port(server_id, 7770)
    assert path == "credentials/servers/test/7770"

    delete_port(server_id, 7770)
    delete_port(server_id, 7771)


@pytest.mark.integration
def test_update_vault_path_nonempty(server_id, port):
    result = update_vault_path(server_id, 2222, "credentials/servers/1/2222")
    assert result == 1

    path = get_vault_path_by_server_port(server_id, 2222)
    assert path == "credentials/servers/1/2222"


@pytest.mark.integration
def test_update_vault_path_empty_deletes(server_id, port):
    update_vault_path(server_id, 2222, "credentials/servers/1/2222")
    result = update_vault_path(server_id, 2222, "")
    assert result == 1

    path = get_vault_path_by_server_port(server_id, 2222)
    assert path is None


@pytest.mark.integration
def test_report_port_result_ok(server_id, port):
    affected = report_port_result(server_id, 2222, ok=True)
    assert affected == 1

    result = load_ports(server_id)
    row = next(r for r in result if r["port"] == 2222)
    assert row["last_success"] is not None


@pytest.mark.integration
def test_report_port_result_fail(server_id, port):
    affected = report_port_result(server_id, 2222, ok=False)
    assert affected == 1

    result = load_ports(server_id)
    row = next(r for r in result if r["port"] == 2222)
    assert row["last_failure"] is not None


@pytest.mark.integration
def test_delete_port(server_id):
    create_port(server_id, 5555)
    affected = delete_port(server_id, 5555)
    assert affected == 1

    ports = [r["port"] for r in load_ports(server_id)]
    assert 5555 not in ports


@pytest.mark.integration
def test_delete_port_not_found(server_id):
    assert delete_port(server_id, 999999) == 0


@pytest.mark.integration
def test_delete_credentials(server_id, port):
    update_vault_path(server_id, 2222, "credentials/servers/1/2222")
    affected = delete_credentials(server_id, 2222)
    assert affected == 1

    path = get_vault_path_by_server_port(server_id, 2222)
    assert path is None
