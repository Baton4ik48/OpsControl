import pytest

from app.services.db.branches_db import create_branch, delete_branch
from app.services.db.servers_db import create_server, delete_server
from app.services.db.ports_db import create_port, delete_port
from app.services.db.tree_db import load_tree


# ============================================
# load_tree
# ============================================


@pytest.mark.integration
def test_load_tree_returns_list():
    result = load_tree()
    assert isinstance(result, list)


@pytest.mark.integration
def test_load_tree_contains_branch():
    branch_id = create_branch("integ-tree-branch")

    rows = load_tree()
    branch_ids = [r[0] for r in rows]
    assert branch_id in branch_ids

    delete_branch(branch_id)


@pytest.mark.integration
def test_load_tree_with_server_and_port():
    branch_id = create_branch("integ-tree-full")
    server_id = create_server(branch_id, "tree-srv", "10.2.0.1", "linux")
    create_port(server_id, 22)

    rows = load_tree()

    # Находим строку с нашим портом
    row = next(
        (r for r in rows if r[0] == branch_id and r[2] == server_id and r[5] == 22),
        None,
    )
    assert row is not None
    assert row[1] == "integ-tree-full"   # branch name
    assert row[3] == "tree-srv"          # server name
    assert row[4] == "10.2.0.1"          # ip

    delete_port(server_id, 22)
    delete_server(server_id)
    delete_branch(branch_id)
