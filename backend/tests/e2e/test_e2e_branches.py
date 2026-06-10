import os
import requests
import pytest

BASE_URL = os.getenv("BACKEND_URL", "http://backend:8000") + "/api"


@pytest.fixture
def branch():
    """Создаёт ветку перед тестом и удаляет после."""
    resp = requests.post(f"{BASE_URL}/branches", json={"name": "e2e-branch"})
    assert resp.status_code == 200
    branch_id = resp.json()["data"]["id"]
    yield branch_id
    requests.delete(f"{BASE_URL}/branches/{branch_id}")


@pytest.mark.e2e
def test_get_branches_returns_list():
    resp = requests.get(f"{BASE_URL}/branches")

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)


@pytest.mark.e2e
def test_get_branches_contains_created(branch):
    resp = requests.get(f"{BASE_URL}/branches")

    ids = [b["id"] for b in resp.json()["data"]]
    assert branch in ids


@pytest.mark.e2e
def test_create_branch_returns_id():
    resp = requests.post(f"{BASE_URL}/branches", json={"name": "e2e-create-test"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["data"]["id"], int)

    requests.delete(f"{BASE_URL}/branches/{body['data']['id']}")


@pytest.mark.e2e
def test_update_branch_changes_name(branch):
    resp = requests.put(
        f"{BASE_URL}/branches/{branch}",
        json={"name": "e2e-branch-updated"},
    )

    assert resp.status_code == 200
    assert resp.json()["success"] is True

    branches = requests.get(f"{BASE_URL}/branches").json()["data"]
    updated = next(b for b in branches if b["id"] == branch)
    assert updated["name"] == "e2e-branch-updated"


@pytest.mark.e2e
def test_update_branch_not_found():
    resp = requests.put(f"{BASE_URL}/branches/999999", json={"name": "nope"})

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Branch not found"


@pytest.mark.e2e
def test_delete_branch():
    create_resp = requests.post(f"{BASE_URL}/branches", json={"name": "e2e-to-delete"})
    branch_id = create_resp.json()["data"]["id"]

    resp = requests.delete(f"{BASE_URL}/branches/{branch_id}")
    assert resp.status_code == 200

    branches = requests.get(f"{BASE_URL}/branches").json()["data"]
    assert not any(b["id"] == branch_id for b in branches)


@pytest.mark.e2e
def test_delete_branch_not_found():
    resp = requests.delete(f"{BASE_URL}/branches/999999")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Branch not found"
