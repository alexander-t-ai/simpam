from datetime import datetime, timezone

import netaddr
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import IPAddress


class IPAddressService:
    def __init__(self, db: Session):
        self.db = db

    def get_ip_address(self, ip_id: int) -> IPAddress:
        obj = self.db.query(IPAddress).filter(IPAddress.id == ip_id).first()
        if not obj:
            raise HTTPException(status_code=404, detail=f"IP address {ip_id} not found")
        return obj

    def list_ip_addresses(
            self,
            address: str | None = None,
            mask_length: int | None = None,
    ) -> list[IPAddress]:
        if address is None and mask_length is None:
            return self.db.query(IPAddress).all()
        results = []
        for record in self.db.query(IPAddress).all():
            try:
                stored = netaddr.IPNetwork(record.address)
                if address is not None and str(stored.ip) != address:
                    continue
                if mask_length is not None and stored.prefixlen != mask_length:
                    continue
                results.append(record)
            except netaddr.AddrFormatError:
                pass
        return results

    def create_ip_address(
            self,
            address: str,
            status: str,
            role: str | None,
            dns_name: str | None,
            description: str | None,
    ) -> IPAddress:
        if self.db.query(IPAddress).filter(IPAddress.address == address).first():
            raise HTTPException(status_code=400, detail="IP address already exists")
        net = netaddr.IPNetwork(address)
        obj = IPAddress(
            address=address,
            family=net.version,
            status=status,
            role=role,
            dns_name=dns_name,
            description=description,
        )
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def patch_ip_address(self, ip_id: int, update_data: dict) -> IPAddress:
        obj = self.get_ip_address(ip_id)
        for field, value in update_data.items():
            if field == "address":
                if value is None:
                    raise HTTPException(status_code=400, detail="address cannot be set to null")
                try:
                    net = netaddr.IPNetwork(value)
                except (netaddr.AddrFormatError, ValueError) as exc:
                    raise HTTPException(status_code=400, detail=f"Invalid address: {value}") from exc
                obj.family = net.version
            setattr(obj, field, value)
        obj.last_updated = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete_ip_address(self, ip_id: int) -> None:
        obj = self.get_ip_address(ip_id)
        self.db.delete(obj)
        self.db.commit()


def get_ip_address_service(db: Session = Depends(get_db)) -> IPAddressService:
    return IPAddressService(db)
