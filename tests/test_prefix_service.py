"""Unit tests for PrefixService using mockito."""
import pytest
from mockito import mock, when, unstub, ANY
from sqlalchemy.exc import IntegrityError

from app.db.models import IPAddress, Prefix, Role
from app.exceptions import AlreadyExistsException, ConflictException, NotFoundException
from app.services.prefix_service import PrefixService


@pytest.fixture(autouse=True)
def cleanup():
    yield
    unstub()


def _prefix(id=1, prefix="10.0.0.0/8", family=4, status="active"):
    p = Prefix()
    p.id = id
    p.prefix = prefix
    p.family = family
    p.status = status
    p.role_id = None
    p.description = None
    return p


def _stub_prefix_query(db):
    """Return (query_mock, filter_mock) for db.query(Prefix) chains."""
    q, f = mock(), mock()
    when(db).query(Prefix).thenReturn(q)
    when(q).filter(ANY).thenReturn(f)
    return q, f


# ---------------------------------------------------------------------------
# get_prefix
# ---------------------------------------------------------------------------

def test_get_prefix_returns_prefix():
    db = mock()
    prefix = _prefix()
    q, f = _stub_prefix_query(db)
    when(f).first().thenReturn(prefix)

    assert PrefixService(db).get_prefix(1) is prefix


def test_get_prefix_not_found_raises():
    db = mock()
    q, f = _stub_prefix_query(db)
    when(f).first().thenReturn(None)

    with pytest.raises(NotFoundException, match="Prefix 99 not found"):
        PrefixService(db).get_prefix(99)


# ---------------------------------------------------------------------------
# list_prefixes
# ---------------------------------------------------------------------------

def test_list_prefixes_no_filters():
    db = mock()
    prefixes = [_prefix(1, "10.0.0.0/8"), _prefix(2, "192.168.0.0/16")]
    q = mock()
    when(db).query(Prefix).thenReturn(q)
    when(q).all().thenReturn(prefixes)

    assert PrefixService(db).list_prefixes(role_name=None, family=None) == prefixes


def test_list_prefixes_unknown_role_raises():
    db = mock()
    role_q, role_f = mock(), mock()
    when(db).query(Role).thenReturn(role_q)
    when(role_q).filter(ANY).thenReturn(role_f)
    when(role_f).first().thenReturn(None)
    when(db).query(Prefix).thenReturn(mock())

    with pytest.raises(ValueError, match="Role 'nonexistent' not found"):
        PrefixService(db).list_prefixes(role_name="nonexistent", family=None)


def test_list_prefixes_filters_by_role():
    db = mock()
    role = Role(); role.id = 5; role.name = "infra"
    prefix = _prefix(); prefix.role_id = 5

    role_q, role_f = mock(), mock()
    when(db).query(Role).thenReturn(role_q)
    when(role_q).filter(ANY).thenReturn(role_f)
    when(role_f).first().thenReturn(role)

    prefix_q, filtered_q = mock(), mock()
    when(db).query(Prefix).thenReturn(prefix_q)
    when(prefix_q).filter(ANY).thenReturn(filtered_q)
    when(filtered_q).all().thenReturn([prefix])

    assert PrefixService(db).list_prefixes(role_name="infra", family=None) == [prefix]


def test_list_prefixes_filters_by_family():
    db = mock()
    prefix = _prefix(family=6, prefix="2001:db8::/32")
    q, filtered_q = mock(), mock()
    when(db).query(Prefix).thenReturn(q)
    when(q).filter(ANY).thenReturn(filtered_q)
    when(filtered_q).all().thenReturn([prefix])

    assert PrefixService(db).list_prefixes(role_name=None, family=6) == [prefix]


# ---------------------------------------------------------------------------
# create_prefix
# ---------------------------------------------------------------------------

def test_create_prefix_success():
    db = mock()
    q, f = _stub_prefix_query(db)
    when(f).first().thenReturn(None)

    result = PrefixService(db).create_prefix("10.0.0.0/8", "active", None, "RFC1918")

    assert result.prefix == "10.0.0.0/8"
    assert result.family == 4
    assert result.status == "active"
    assert result.description == "RFC1918"


def test_create_prefix_already_exists_raises():
    db = mock()
    q, f = _stub_prefix_query(db)
    when(f).first().thenReturn(_prefix())

    with pytest.raises(AlreadyExistsException):
        PrefixService(db).create_prefix("10.0.0.0/8", "active", None, None)


# ---------------------------------------------------------------------------
# delete_prefix
# ---------------------------------------------------------------------------

def test_delete_prefix_success():
    db = mock()
    q, f = _stub_prefix_query(db)
    when(f).first().thenReturn(_prefix())

    PrefixService(db).delete_prefix(1)  # should not raise


# ---------------------------------------------------------------------------
# allocate_ip
# ---------------------------------------------------------------------------

def test_allocate_ip_success():
    db = mock()
    parent = _prefix(prefix="10.0.0.0/30")
    q, f = _stub_prefix_query(db)
    when(f).first().thenReturn(parent)

    ip_q = mock()
    when(db).query(IPAddress).thenReturn(ip_q)
    when(ip_q).all().thenReturn([])

    result = PrefixService(db).allocate_ip(1)

    assert result.address == "10.0.0.1/30"
    assert result.family == 4
    assert result.status == "active"


def test_allocate_ip_no_available_raises():
    db = mock()
    parent = _prefix(prefix="10.0.0.0/30")
    q, f = _stub_prefix_query(db)
    when(f).first().thenReturn(parent)

    allocated = []
    for addr in ["10.0.0.1", "10.0.0.2"]:
        ip = IPAddress(); ip.address = f"{addr}/30"
        allocated.append(ip)

    ip_q = mock()
    when(db).query(IPAddress).thenReturn(ip_q)
    when(ip_q).all().thenReturn(allocated)

    with pytest.raises(ConflictException, match="No available IPs"):
        PrefixService(db).allocate_ip(1)


# ---------------------------------------------------------------------------
# allocate_prefix
# ---------------------------------------------------------------------------

def test_allocate_prefix_success():
    db = mock()
    parent = _prefix(prefix="10.0.0.0/24")
    q, f = _stub_prefix_query(db)
    when(f).first().thenReturn(parent)
    when(q).all().thenReturn([])  # no child prefixes

    result = PrefixService(db).allocate_prefix(1, 26)

    assert result.prefix == "10.0.0.0/26"
    assert result.family == 4

def test_allocate_v6_prefix_success():
    db = mock()
    parent = _prefix(prefix="2a02:1400:9::/64")
    q, f = _stub_prefix_query(db)
    when(f).first().thenReturn(parent)
    when(q).all().thenReturn([])  # no child prefixes

    result = PrefixService(db).allocate_prefix(1, 127)

    assert result.prefix == "2a02:1400:9::/127"
    assert result.family == 6


def test_allocate_prefix_length_too_small_raises():
    db = mock()
    parent = _prefix(prefix="10.0.0.0/24")
    q, f = _stub_prefix_query(db)
    when(f).first().thenReturn(parent)

    with pytest.raises(ValueError, match="must be greater than parent"):
        PrefixService(db).allocate_prefix(1, 24)


def test_allocate_prefix_length_too_large_raises():
    db = mock()
    parent = _prefix(prefix="10.0.0.0/24")
    q, f = _stub_prefix_query(db)
    when(f).first().thenReturn(parent)

    with pytest.raises(ValueError, match="Invalid prefix_length"):
        PrefixService(db).allocate_prefix(1, 33)
