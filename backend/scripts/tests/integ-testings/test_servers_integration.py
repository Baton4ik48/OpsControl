import pytest

from app.services.db.branches_db import create_branch, delete_branch
from app.services.db.servers_db import (
    load_servers,
    create_server,
    update_server,
    delete_server,
)


@pytest.fixture
def branch():
    branch_id = create_branch("integ-servers-branch")
    yield branch_id
    delete_branch(branch_id)


@pytest.fixture
def server(branch):
    server_id = create_server(branch, "integ-srv", "10.0.0.1", "linux")
    yield server_id
    delete_server(server_id)


# ============================================
# load_servers
# ============================================


@pytest.mark.integration
def test_load_servers_empty(branch):
    result = load_servers(branch)
    assert result == []


@pytest.mark.integration
def test_load_servers_returns_created(server, branch):
    rows = load_servers(branch)
    ids = [r[0] for r in rows]
    assert server in ids


@pytest.mark.integration
def test_load_servers_row_structure(server, branch):
    rows = load_servers(branch)
    row = next(r for r in rows if r[0] == server)
    assert row[1] == "integ-srv"
    assert row[2] == "10.0.0.1"
    assert row[3] == "linux"


# ============================================
# create_server
# ============================================


@pytest.mark.integration
def test_create_server_returns_int(branch):
    server_id = create_server(branch, "integ-create", "10.0.0.2", "linux")
    assert isinstance(server_id, int)
    delete_server(server_id)


@pytest.mark.integration
def test_create_server_default_device_type(branch):
    server_id = create_server(branch, "integ-default", "10.0.0.3")
    rows = load_servers(branch)
    row = next(r for r in rows if r[0] == server_id)
    assert row[3] == "linux"
    delete_server(server_id)


# ============================================
# update_server
# ============================================


@pytest.mark.integration
def test_update_server_changes_data(server, branch):
    affected = update_server(server, "integ-srv-updated", "10.0.0.99", "cisco")
    assert affected == 1

    rows = load_servers(branch)
    row = next(r for r in rows if r[0] == server)
    assert row[1] == "integ-srv-updated"
    assert row[2] == "10.0.0.99"
    assert row[3] == "cisco"


@pytest.mark.integration
def test_update_server_not_found():
    affected = update_server(999999, "x", "1.2.3.4")
    assert affected == 0


# ============================================
# delete_server
# ============================================


@pytest.mark.integration
def test_delete_server(branch):
    server_id = create_server(branch, "integ-to-delete", "10.0.0.4")
    affected = delete_server(server_id)
    assert affected == 1

    rows = load_servers(branch)
    assert not any(r[0] == server_id for r in rows)


@pytest.mark.integration
def test_delete_server_not_found():
    affected = delete_server(999999)
    assert affected == 0
