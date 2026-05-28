"""Integration tests for roles endpoints."""
import requests

BASE_URL = "http://localhost:8000/api"
ROLES_URL = f"{BASE_URL}/ipam/roles"
RESET_URL = f"{BASE_URL}/reset"


def test_create_and_list_roles():
    r1 = requests.post(f"{ROLES_URL}/", json={"name": "management"})
    assert r1.status_code == 201
    assert r1.json()["name"] == "management"
    assert r1.json()["id"] > 0

    r2 = requests.post(f"{ROLES_URL}/", json={"name": "loopback"})
    assert r2.status_code == 201

    resp = requests.get(f"{ROLES_URL}/")
    assert resp.status_code == 200
    names = [r["name"] for r in resp.json()]
    assert "management" in names
    assert "loopback" in names


def test_duplicate_role_rejected():
    requests.post(f"{ROLES_URL}/", json={"name": "unique-role"})
    resp = requests.post(f"{ROLES_URL}/", json={"name": "unique-role"})
    assert resp.status_code == 400


def test_reset_entity_ip_address():
    requests.post(f"{BASE_URL}/ipam/ip-addresses/", json={"address": "10.1.1.1/24"})
    requests.post(f"{ROLES_URL}/", json={"name": "keep-me"})

    resp = requests.post(f"{RESET_URL}/", params={"entity": "ip-address"})
    assert resp.status_code == 204

    ips = requests.get(f"{BASE_URL}/ipam/ip-addresses/").json()
    assert ips["count"] == 0

    roles = requests.get(f"{ROLES_URL}/").json()
    assert any(r["name"] == "keep-me" for r in roles)


def test_reset_entity_unknown_returns_400():
    resp = requests.post(f"{RESET_URL}/", params={"entity": "foobar"})
    assert resp.status_code == 400
