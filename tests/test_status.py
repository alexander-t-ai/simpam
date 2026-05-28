"""Integration tests for the status endpoint."""
import requests

BASE_URL = "http://localhost:8000/api/v1"


def test_status():
    resp = requests.get(f"{BASE_URL}/status/")
    assert resp.status_code == 200
    assert resp.json() == {"netbox-version": "Simpam 67"}
