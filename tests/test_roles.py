"""Integration tests for roles endpoints."""
import requests

BASE_URL = "http://localhost:8000/api"
ROLES_URL = f"{BASE_URL}/ipam/roles"


def test_create_and_list_roles():
    # Roles persist across resets; accept 201 (new) or 400 (already exists)
    for name in ("management", "loopback"):
        resp = requests.post(f"{ROLES_URL}/", json={"name": name})
        assert resp.status_code in (201, 400)

    resp = requests.get(f"{ROLES_URL}/")
    assert resp.status_code == 200
    names = [r["name"] for r in resp.json()]
    assert "management" in names
    assert "loopback" in names


def test_create_role_returns_201():
    import uuid
    name = f"test-{uuid.uuid4().hex[:8]}"
    resp = requests.post(f"{ROLES_URL}/", json={"name": name})
    assert resp.status_code == 201
    assert resp.json()["name"] == name
    assert resp.json()["id"] > 0


def test_duplicate_role_rejected():
    requests.post(f"{ROLES_URL}/", json={"name": "unique-role"})
    resp = requests.post(f"{ROLES_URL}/", json={"name": "unique-role"})
    assert resp.status_code == 400
