import pytest

from app.services.db.branches_db import (
    load_branches,
    create_branch,
    update_branch,
    delete_branch,
)


@pytest.fixture
def branch():
    """Создаёт ветку перед тестом и удаляет после."""
    branch_id = create_branch("integ-test-branch")
    yield branch_id
    delete_branch(branch_id)


@pytest.mark.integration
def test_load_branches_returns_list():
    result = load_branches()
    assert isinstance(result, list)


@pytest.mark.integration
def test_load_branches_contains_created(branch):
    rows = load_branches()
    ids = [r[0] for r in rows]
    assert branch in ids


@pytest.mark.integration
def test_create_branch_returns_int():
    branch_id = create_branch("integ-create-test")
    assert isinstance(branch_id, int)
    delete_branch(branch_id)  # cleanup


@pytest.mark.integration
def test_create_branch_appears_in_list():
    branch_id = create_branch("integ-create-appears")

    rows = load_branches()
    names = [r[1] for r in rows]
    assert "integ-create-appears" in names

    delete_branch(branch_id)  # cleanup


@pytest.mark.integration
def test_update_branch_changes_name(branch):
    affected = update_branch(branch, "integ-test-branch-updated")
    assert affected == 1

    rows = load_branches()
    names = [r[1] for r in rows]
    assert "integ-test-branch-updated" in names


@pytest.mark.integration
def test_update_branch_not_found():
    affected = update_branch(999999, "nope")
    assert affected == 0


@pytest.mark.integration
def test_delete_branch_removes_from_list():
    branch_id = create_branch("integ-to-delete")

    affected = delete_branch(branch_id)
    assert affected == 1

    rows = load_branches()
    ids = [r[0] for r in rows]
    assert branch_id not in ids


@pytest.mark.integration
def test_delete_branch_not_found():
    affected = delete_branch(999999)
    assert affected == 0
