from datetime import datetime
from typing import Any

import netaddr
from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _family_obj(value: int) -> dict:
    return {"value": value, "label": "IPv4" if value == 4 else "IPv6"}


def _status_obj(value: str) -> dict:
    label_map = {
        "active": "Active",
        "reserved": "Reserved",
        "deprecated": "Deprecated",
        "container": "Container",
        "dhcp": "DHCP",
        "slaac": "SLAAC",
    }
    return {"value": value, "label": label_map.get(value, value.capitalize())}


VALID_IP_ROLES = frozenset({"loopback", "secondary", "anycast", "vip", "vrrp", "hsrp", "glbp", "carp"})

_IP_ROLE_LABELS = {
    "loopback": "Loopback",
    "secondary": "Secondary",
    "anycast": "Anycast",
    "vip": "VIP",
    "vrrp": "VRRP",
    "hsrp": "HSRP",
    "glbp": "GLBP",
    "carp": "CARP",
}


def _ip_role_obj(value: str) -> dict:
    return {"value": value, "label": _IP_ROLE_LABELS.get(value, value.upper())}


# ---------------------------------------------------------------------------
# Role schemas
# ---------------------------------------------------------------------------

class RoleCreate(BaseModel):
    name: str


class RoleResponse(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Prefix schemas
# ---------------------------------------------------------------------------

class PrefixCreate(BaseModel):
    prefix: str
    status: str = "active"
    role_id: int | None = None
    description: str | None = None

    @field_validator("prefix")
    @classmethod
    def validate_prefix(cls, v: str) -> str:
        try:
            netaddr.IPNetwork(v)
        except (netaddr.AddrFormatError, ValueError) as exc:
            raise ValueError(f"Invalid prefix: {v}") from exc
        return v


class PrefixResponse(BaseModel):
    id: int
    prefix: str
    family: dict[str, Any]
    status: dict[str, Any]
    role: RoleResponse | None
    description: str
    created: datetime
    last_updated: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_obj(cls, obj: Any) -> "PrefixResponse":
        return cls(
            id=obj.id,
            prefix=obj.prefix,
            family=_family_obj(obj.family),
            status=_status_obj(obj.status),
            role=RoleResponse(id=obj.role.id, name=obj.role.name) if obj.role else None,
            description=obj.description or "",
            created=obj.created,
            last_updated=obj.last_updated,
        )


class PrefixListResponse(BaseModel):
    count: int
    results: list[PrefixResponse]


# ---------------------------------------------------------------------------
# Available IPs / Prefixes (lightweight objects)
# ---------------------------------------------------------------------------

class AvailableIP(BaseModel):
    address: str
    family: dict[str, Any]


class AvailablePrefix(BaseModel):
    prefix: str
    family: dict[str, Any]


class AvailablePrefixRequest(BaseModel):
    prefix_length: int


# ---------------------------------------------------------------------------
# IP Address schemas
# ---------------------------------------------------------------------------

class IPAddressCreate(BaseModel):
    address: str
    status: str = "active"
    role: str | None = None
    dns_name: str | None = None
    description: str | None = None

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        try:
            netaddr.IPNetwork(v)
        except (netaddr.AddrFormatError, ValueError) as exc:
            raise ValueError(f"Invalid address: {v}") from exc
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str | None) -> str | None:
        if v is not None and v.lower() not in VALID_IP_ROLES:
            raise ValueError(f"Invalid role '{v}'. Must be one of: {', '.join(sorted(VALID_IP_ROLES))}")
        return v.lower() if v is not None else None


class IPAddressPatch(BaseModel):
    address: str | None = None
    status: str | None = None
    role: str | None = None
    dns_name: str | None = None
    description: str | None = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str | None) -> str | None:
        if v is not None and v.lower() not in VALID_IP_ROLES:
            raise ValueError(f"Invalid role '{v}'. Must be one of: {', '.join(sorted(VALID_IP_ROLES))}")
        return v.lower() if v is not None else None


class IPAddressResponse(BaseModel):
    id: int
    address: str
    family: dict[str, Any]
    status: dict[str, Any]
    role: dict[str, str] | None
    dns_name: str
    description: str
    created: datetime
    last_updated: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_obj(cls, obj: Any) -> "IPAddressResponse":
        return cls(
            id=obj.id,
            address=obj.address,
            family=_family_obj(obj.family),
            status=_status_obj(obj.status),
            role=_ip_role_obj(obj.role) if obj.role else None,
            dns_name=obj.dns_name or "",
            description=obj.description or "",
            created=obj.created,
            last_updated=obj.last_updated,
        )


class IPAddressListResponse(BaseModel):
    count: int
    results: list[IPAddressResponse]
