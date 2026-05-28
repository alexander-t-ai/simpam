"""Integration tests for IP address endpoints."""
import requests

BASE_URL = "http://localhost:8000/api/v1"
IPAM_URL = f"{BASE_URL}/ipam"
IPS_URL = f"{IPAM_URL}/ip-addresses"
PREFIXES_URL = f"{IPAM_URL}/prefixes"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_ip(address: str, **kwargs) -> dict:
    payload = {"address": address, **kwargs}
    resp = requests.post(f"{IPS_URL}/", json=payload)
    assert resp.status_code == 201, f"Failed to create IP: {resp.text}"
    return resp.json()


# ---------------------------------------------------------------------------
# Test 1: Create an IP address, get it by ID
# ---------------------------------------------------------------------------

def test_create_and_get_ip():
    created = create_ip("192.168.1.10/24", description="test host")
    ip_id = created["id"]

    assert created["address"] == "192.168.1.10/24"
    assert created["family"]["value"] == 4
    assert created["status"]["value"] == "active"
    assert created["description"] == "test host"
    assert created["role"] is None

    get_resp = requests.get(f"{IPS_URL}/{ip_id}/")
    assert get_resp.status_code == 200
    fetched = get_resp.json()
    assert fetched["id"] == ip_id
    assert fetched["address"] == "192.168.1.10/24"


# ---------------------------------------------------------------------------
# Test 2: PATCH description
# ---------------------------------------------------------------------------

def test_patch_ip_description():
    created = create_ip("10.0.0.5/24", description="original")
    ip_id = created["id"]

    patch_resp = requests.patch(
        f"{IPS_URL}/{ip_id}/",
        json={"description": "updated description"},
    )
    assert patch_resp.status_code == 200
    patched = patch_resp.json()
    assert patched["description"] == "updated description"
    assert patched["address"] == "10.0.0.5/24"

    get_resp = requests.get(f"{IPS_URL}/{ip_id}/").json()
    assert get_resp["description"] == "updated description"


# ---------------------------------------------------------------------------
# Test 3: Delete an IP, verify 404
# ---------------------------------------------------------------------------

def test_delete_ip():
    created = create_ip("10.0.0.100/24")
    ip_id = created["id"]

    del_resp = requests.delete(f"{IPS_URL}/{ip_id}/")
    assert del_resp.status_code == 204

    get_resp = requests.get(f"{IPS_URL}/{ip_id}/")
    assert get_resp.status_code == 404


# ---------------------------------------------------------------------------
# Test 4: Filter by address and mask_length
# ---------------------------------------------------------------------------

def test_filter_by_address():
    create_ip("10.1.1.1/24")
    create_ip("10.1.1.2/24")
    create_ip("10.2.2.1/16")

    resp = requests.get(f"{IPS_URL}/", params={"address": "10.1.1.1"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["results"][0]["address"] == "10.1.1.1/24"


def test_filter_by_mask_length():
    create_ip("10.1.1.1/24")
    create_ip("10.1.1.2/24")
    create_ip("10.2.2.1/16")

    resp = requests.get(f"{IPS_URL}/", params={"mask_length": 24})
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2
    for item in data["results"]:
        assert item["address"].endswith("/24")


def test_filter_by_address_and_mask_length():
    create_ip("10.1.1.1/24")
    create_ip("10.1.1.1/16")

    resp = requests.get(f"{IPS_URL}/", params={"address": "10.1.1.1", "mask_length": 24})
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["results"][0]["address"] == "10.1.1.1/24"


# ---------------------------------------------------------------------------
# Test 5: Allocate IP via prefix
# ---------------------------------------------------------------------------

def test_allocate_ip_via_prefix():
    prefix_resp = requests.post(f"{PREFIXES_URL}/", json={"prefix": "172.16.0.0/30"})
    assert prefix_resp.status_code == 201
    prefix_id = prefix_resp.json()["id"]

    alloc_resp = requests.post(f"{PREFIXES_URL}/{prefix_id}/available-ips/")
    assert alloc_resp.status_code == 201
    allocated = alloc_resp.json()

    assert allocated["address"] == "172.16.0.1/30"
    assert allocated["family"]["value"] == 4
    assert allocated["status"]["value"] == "active"
    assert "id" in allocated
    assert allocated["id"] > 0

    list_resp = requests.get(f"{IPS_URL}/").json()
    addresses = [r["address"] for r in list_resp["results"]]
    assert "172.16.0.1/30" in addresses


# ---------------------------------------------------------------------------
# Test 6: IPv6 address creation and retrieval
# ---------------------------------------------------------------------------

def test_ipv6_address():
    created = create_ip("2001:db8::1/128", description="IPv6 host")
    assert created["family"]["value"] == 6
    assert created["address"] == "2001:db8::1/128"

    get_resp = requests.get(f"{IPS_URL}/{created['id']}/").json()
    assert get_resp["family"]["value"] == 6


# ---------------------------------------------------------------------------
# Test 7: PATCH dns_name and role
# ---------------------------------------------------------------------------

def test_patch_dns_name_and_role():
    created = create_ip("10.99.0.1/24")
    ip_id = created["id"]

    patch_resp = requests.patch(
        f"{IPS_URL}/{ip_id}/",
        json={"dns_name": "host.example.com", "role": "loopback"},
    )
    assert patch_resp.status_code == 200
    patched = patch_resp.json()
    assert patched["dns_name"] == "host.example.com"
    assert patched["role"]["value"] == "loopback"
    assert patched["role"]["label"] == "Loopback"


# ---------------------------------------------------------------------------
# Test 8: Create IP with role
# ---------------------------------------------------------------------------

def test_create_ip_with_role():
    created = create_ip("10.88.0.1/24", role="vip")

    assert created["role"] is not None
    assert created["role"]["value"] == "vip"
    assert created["role"]["label"] == "VIP"


# ---------------------------------------------------------------------------
# Test 9: Invalid role rejected
# ---------------------------------------------------------------------------

def test_invalid_role_rejected():
    resp = requests.post(f"{IPS_URL}/", json={"address": "10.77.0.1/24", "role": "management"})
    assert resp.status_code == 422
