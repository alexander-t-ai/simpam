"""Integration tests for prefix endpoints."""
import requests

BASE_URL = "http://localhost:8000/api"
IPAM_URL = f"{BASE_URL}/ipam"
PREFIXES_URL = f"{IPAM_URL}/prefixes"
ROLES_URL = f"{IPAM_URL}/roles"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_role(name: str) -> dict:
    resp = requests.post(f"{ROLES_URL}/", json={"name": name})
    assert resp.status_code == 201, f"Failed to create role: {resp.text}"
    return resp.json()


def create_prefix(prefix: str, role_id: int | None = None, **kwargs) -> dict:
    payload = {"prefix": prefix, **kwargs}
    if role_id is not None:
        payload["role_id"] = role_id
    resp = requests.post(f"{PREFIXES_URL}/", json=payload)
    assert resp.status_code == 201, f"Failed to create prefix: {resp.text}"
    return resp.json()


# ---------------------------------------------------------------------------
# Test 1: Create a prefix, list it, verify it appears
# ---------------------------------------------------------------------------

def test_create_and_list_prefix():
    created = create_prefix("10.0.0.0/24")
    assert created["prefix"] == "10.0.0.0/24"
    assert created["id"] > 0
    assert created["family"]["value"] == 4
    assert created["status"]["value"] == "active"
    assert created["role"] is None

    resp = requests.get(f"{PREFIXES_URL}/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["results"][0]["prefix"] == "10.0.0.0/24"


# ---------------------------------------------------------------------------
# Test 2: Available IPs do not include network/broadcast
# ---------------------------------------------------------------------------

def test_available_ips_excludes_network_broadcast():
    created = create_prefix("192.168.1.0/24")
    prefix_id = created["id"]

    resp = requests.get(f"{PREFIXES_URL}/{prefix_id}/available-ips/")
    assert resp.status_code == 200
    ips = resp.json()

    addresses = [entry["address"].split("/")[0] for entry in ips]

    assert "192.168.1.0" not in addresses
    assert "192.168.1.255" not in addresses
    assert "192.168.1.1" in addresses
    assert "192.168.1.254" in addresses
    assert len(ips) == 254


# ---------------------------------------------------------------------------
# Test 3: Allocate an IP, then verify it's no longer available
# ---------------------------------------------------------------------------

def test_allocate_ip_removes_from_available():
    created = create_prefix("10.1.0.0/30")
    prefix_id = created["id"]

    avail_before = requests.get(f"{PREFIXES_URL}/{prefix_id}/available-ips/").json()
    assert len(avail_before) == 2

    alloc_resp = requests.post(f"{PREFIXES_URL}/{prefix_id}/available-ips/")
    assert alloc_resp.status_code == 201
    allocated = alloc_resp.json()
    assert allocated["address"] == "10.1.0.1/30"
    assert allocated["id"] > 0
    assert allocated["family"]["value"] == 4

    avail_after = requests.get(f"{PREFIXES_URL}/{prefix_id}/available-ips/").json()
    assert len(avail_after) == 1
    assert avail_after[0]["address"] == "10.1.0.2/30"


# ---------------------------------------------------------------------------
# Test 4: Delete a prefix, verify 404
# ---------------------------------------------------------------------------

def test_delete_prefix():
    created = create_prefix("172.16.0.0/16")
    prefix_id = created["id"]

    del_resp = requests.delete(f"{PREFIXES_URL}/{prefix_id}/")
    assert del_resp.status_code == 204

    get_resp = requests.get(f"{PREFIXES_URL}/{prefix_id}/")
    assert get_resp.status_code == 404


# ---------------------------------------------------------------------------
# Test 5: Filter prefixes by role
# ---------------------------------------------------------------------------

def test_filter_by_role():
    prod = create_role("production")
    staging = create_role("staging")

    create_prefix("10.10.0.0/24", role_id=prod["id"])
    create_prefix("10.20.0.0/24", role_id=staging["id"])
    create_prefix("10.30.0.0/24", role_id=prod["id"])

    resp = requests.get(f"{PREFIXES_URL}/", params={"role": "production"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2
    for item in data["results"]:
        assert item["role"]["name"] == "production"
        assert item["role"]["id"] == prod["id"]

    resp2 = requests.get(f"{PREFIXES_URL}/", params={"role": "staging"})
    data2 = resp2.json()
    assert data2["count"] == 1
    assert data2["results"][0]["prefix"] == "10.20.0.0/24"


# ---------------------------------------------------------------------------
# Test 6: Filter prefixes by family
# ---------------------------------------------------------------------------

def test_filter_by_family():
    create_prefix("10.0.0.0/8")
    create_prefix("172.16.0.0/12")
    create_prefix("2001:db8::/32")

    resp4 = requests.get(f"{PREFIXES_URL}/", params={"family": 4})
    assert resp4.status_code == 200
    data4 = resp4.json()
    assert data4["count"] == 2
    for item in data4["results"]:
        assert item["family"]["value"] == 4

    resp6 = requests.get(f"{PREFIXES_URL}/", params={"family": 6})
    data6 = resp6.json()
    assert data6["count"] == 1
    assert data6["results"][0]["family"]["value"] == 6


# ---------------------------------------------------------------------------
# Test 7: Available-prefixes and allocate child prefix
# ---------------------------------------------------------------------------

def test_allocate_child_prefix():
    parent = create_prefix("10.0.0.0/24")
    prefix_id = parent["id"]

    avail = requests.get(f"{PREFIXES_URL}/{prefix_id}/available-prefixes/").json()
    assert len(avail) >= 1

    alloc = requests.post(
        f"{PREFIXES_URL}/{prefix_id}/available-prefixes/",
        json={"prefix_length": 26},
    )
    assert alloc.status_code == 201
    child = alloc.json()
    assert child["prefix"].endswith("/26")
    assert child["family"]["value"] == 4

    list_resp = requests.get(f"{PREFIXES_URL}/").json()
    prefixes_list = [p["prefix"] for p in list_resp["results"]]
    assert child["prefix"] in prefixes_list

    avail_after = requests.get(f"{PREFIXES_URL}/{prefix_id}/available-prefixes/").json()
    avail_prefixes = [a["prefix"] for a in avail_after]
    assert child["prefix"] not in avail_prefixes


# ---------------------------------------------------------------------------
# Test 8: Allocate child prefix with status and description
# ---------------------------------------------------------------------------

def test_allocate_child_prefix_with_status_and_description():
    parent = create_prefix("10.100.0.0/16")
    prefix_id = parent["id"]

    alloc = requests.post(
        f"{PREFIXES_URL}/{prefix_id}/available-prefixes/",
        json={"prefix_length": 24, "status": "reserved", "description": "test subnet"},
    )
    assert alloc.status_code == 201
    child = alloc.json()
    assert child["prefix"] == "10.100.0.0/24"
    assert child["status"]["value"] == "reserved"
    assert child["description"] == "test subnet"


def test_allocate_child_prefix_length_too_small():
    parent = create_prefix("10.101.0.0/24")
    resp = requests.post(
        f"{PREFIXES_URL}/{parent['id']}/available-prefixes/",
        json={"prefix_length": 16},
    )
    assert resp.status_code == 400


def test_allocate_child_prefix_length_too_large():
    parent = create_prefix("10.102.0.0/24")
    resp = requests.post(
        f"{PREFIXES_URL}/{parent['id']}/available-prefixes/",
        json={"prefix_length": 33},
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Test 9: Get prefix by ID
# ---------------------------------------------------------------------------

def test_get_prefix_by_id():
    created = create_prefix("10.50.0.0/24")
    resp = requests.get(f"{PREFIXES_URL}/{created['id']}/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == created["id"]
    assert data["prefix"] == "10.50.0.0/24"
    assert data["family"]["value"] == 4
    assert data["status"]["value"] == "active"
    assert data["role"] is None


def test_get_nonexistent_prefix_returns_404():
    resp = requests.get(f"{PREFIXES_URL}/99999/")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Test 9: Filter by nonexistent role returns 400
# ---------------------------------------------------------------------------

def test_filter_by_nonexistent_role():
    resp = requests.get(f"{PREFIXES_URL}/", params={"role": "does-not-exist"})
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Test 9: Prefix with role shows role object in response
# ---------------------------------------------------------------------------

def test_prefix_role_response():
    role = create_role("infra")
    created = create_prefix("192.0.2.0/24", role_id=role["id"])

    assert created["role"] is not None
    assert created["role"]["id"] == role["id"]
    assert created["role"]["name"] == "infra"

    fetched = requests.get(f"{PREFIXES_URL}/{created['id']}/").json()
    assert fetched["role"]["name"] == "infra"
