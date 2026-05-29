import netaddr
from fastapi import Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import IPAddress, Prefix, Role
from app.exceptions import AlreadyExistsException, ConflictException, NotFoundException


class PrefixService:
    def __init__(self, db: Session):
        self.db = db

    def get_prefix(self, prefix_id: int) -> Prefix:
        obj = self.db.query(Prefix).filter(Prefix.id == prefix_id).first()
        if not obj:
            raise NotFoundException(f"Prefix {prefix_id} not found")
        return obj

    def list_prefixes(self, role: str | None, family: int | None) -> list[Prefix]:
        q = self.db.query(Prefix)
        if role is not None:
            role_obj = self.db.query(Role).filter(Role.name == role).first()
            if role_obj is None:
                raise ValueError(f"Role '{role}' not found")
            q = q.filter(Prefix.role_id == role_obj.id)
        if family is not None:
            q = q.filter(Prefix.family == family)
        return q.all()

    def create_prefix(self, prefix: str, status: str, role_id: int | None, description: str | None) -> Prefix:
        if self.db.query(Prefix).filter(Prefix.prefix == prefix).first():
            raise AlreadyExistsException("Prefix already exists")
        net = netaddr.IPNetwork(prefix)
        obj = Prefix(
            prefix=str(net),
            family=net.version,
            status=status,
            role_id=role_id,
            description=description,
        )
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete_prefix(self, prefix_id: int) -> None:
        obj = self.get_prefix(prefix_id)
        self.db.delete(obj)
        self.db.commit()

    def get_available_ips(self, prefix_id: int) -> tuple[netaddr.IPNetwork, list[netaddr.IPAddress]]:
        obj = self.get_prefix(prefix_id)
        net = netaddr.IPNetwork(obj.prefix)
        allocated = self._allocated_ips_in_prefix(net)
        available = [ip for ip in _usable_hosts(net) if ip not in allocated]
        return net, available

    def allocate_ip(self, prefix_id: int) -> IPAddress:
        net, available = self.get_available_ips(prefix_id)
        if not available:
            raise ConflictException("No available IPs in prefix")
        ip_obj = IPAddress(address=f"{available[0]}/{net.prefixlen}", family=net.version, status="active")
        try:
            self.db.add(ip_obj)
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise ConflictException("Address already allocated")
        self.db.refresh(ip_obj)
        return ip_obj

    def get_available_prefixes(self, prefix_id: int) -> tuple[netaddr.IPNetwork, list[netaddr.IPNetwork]]:
        obj = self.get_prefix(prefix_id)
        net = netaddr.IPNetwork(obj.prefix)
        return net, _available_subnets(net, self._child_prefixes(net))

    def allocate_prefix(self, prefix_id: int, prefix_length: int, status: str = "active", description: str | None = None) -> Prefix:
        obj = self.get_prefix(prefix_id)
        net = netaddr.IPNetwork(obj.prefix)

        if prefix_length <= net.prefixlen:
            raise ValueError(f"Requested prefix_length {prefix_length} must be greater than parent prefix length {net.prefixlen}")
        if prefix_length > (32 if net.version == 4 else 128):
            raise ValueError("Invalid prefix_length")

        available_blocks = _available_subnets(net, self._child_prefixes(net))
        chosen = None
        for block in sorted(available_blocks, key=lambda x: x.network):
            if block.prefixlen <= prefix_length:
                subnets = list(block.subnet(prefix_length))
                if subnets:
                    chosen = subnets[0]
                    break

        if chosen is None:
            raise ConflictException("No available prefix of requested size")

        new_prefix = Prefix(prefix=str(chosen.cidr), family=net.version, status=status, description=description)
        try:
            self.db.add(new_prefix)
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise ConflictException("Prefix already exists")
        self.db.refresh(new_prefix)
        return new_prefix

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _allocated_ips_in_prefix(self, net: netaddr.IPNetwork) -> set[netaddr.IPAddress]:
        allocated = set()
        for record in self.db.query(IPAddress).all():
            try:
                ip = netaddr.IPNetwork(record.address).ip
                if ip in net:
                    allocated.add(ip)
            except netaddr.AddrFormatError:
                pass
        return allocated

    def _child_prefixes(self, parent: netaddr.IPNetwork) -> list[netaddr.IPNetwork]:
        children = []
        for p in self.db.query(Prefix).all():
            try:
                net = netaddr.IPNetwork(p.prefix)
                if net != parent and net.prefixlen >= parent.prefixlen and net in parent:
                    children.append(net)
            except netaddr.AddrFormatError:
                pass
        return children


def get_prefix_service(db: Session = Depends(get_db)) -> PrefixService:
    return PrefixService(db)


# ---------------------------------------------------------------------------
# Pure helpers (no db dependency)
# ---------------------------------------------------------------------------

def _usable_hosts(net: netaddr.IPNetwork) -> list[netaddr.IPAddress]:
    if net.version == 4:
        if net.prefixlen == 32:
            return [net.ip]
        if net.prefixlen == 31:
            return list(net)
        return list(net.iter_hosts())
    else:
        if net.prefixlen == 128:
            return [net.ip]
        return list(net.iter_hosts())


def _available_subnets(parent: netaddr.IPNetwork, children: list[netaddr.IPNetwork]) -> list[netaddr.IPNetwork]:
    if not children:
        return [parent]
    remaining = [parent]
    for child in children:
        new_remaining = []
        for block in remaining:
            try:
                new_remaining.extend(netaddr.cidr_exclude(block, child))
            except Exception:
                new_remaining.append(block)
        remaining = new_remaining
    return remaining
