import pytest
import requests

BASE_URL = "http://localhost:8000/api"
IPAM_URL = f"{BASE_URL}/ipam"


@pytest.fixture(autouse=True)
def reset_db():
    """Clear all tables before each test."""
    resp = requests.post(f"{BASE_URL}/reset/")
    assert resp.status_code == 204, f"Reset failed: {resp.status_code} {resp.text}"
