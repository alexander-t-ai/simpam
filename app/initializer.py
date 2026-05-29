import logging
import os

import netaddr
import yaml
from sqlalchemy.orm import Session

from app.db.models import Prefix, Role

INITIALIZERS_DIR = os.getenv("INITIALIZERS_DIR", "/initializers")
logger = logging.getLogger("ipam")


def run(db: Session) -> None:
    _load_roles(db)
    _load_prefixes(db)


def _load_roles(db: Session) -> None:
    path = os.path.join(INITIALIZERS_DIR, "prefix_vlan_roles.yml")
    try:
        with open(path) as f:
            entries = yaml.safe_load(f) or []
    except FileNotFoundError:
        return

    for entry in entries:
        name = entry.get("name")
        if not name:
            continue
        if db.query(Role).filter(Role.name == name).first():
            continue
        db.add(Role(name=name, description=entry.get("description")))
        logger.info("initializer: created role '%s'", name)

    db.commit()


def _load_prefixes(db: Session) -> None:
    path = os.path.join(INITIALIZERS_DIR, "prefixes.yml")
    try:
        with open(path) as f:
            entries = yaml.safe_load(f) or []
    except FileNotFoundError:
        return

    for entry in entries:
        prefix_str = entry.get("prefix")
        if not prefix_str:
            continue
        if db.query(Prefix).filter(Prefix.prefix == prefix_str).first():
            continue

        role_id = None
        role_name = entry.get("role")
        if role_name:
            role_obj = db.query(Role).filter(Role.name == role_name).first()
            if role_obj:
                role_id = role_obj.id
            else:
                logger.warning("initializer: role '%s' not found for prefix %s, skipping role", role_name, prefix_str)

        try:
            net = netaddr.IPNetwork(prefix_str)
        except (netaddr.AddrFormatError, ValueError):
            logger.warning("initializer: invalid prefix '%s', skipping", prefix_str)
            continue

        db.add(Prefix(
            prefix=prefix_str,
            family=net.version,
            status=entry.get("status", "active"),
            role_id=role_id,
            description=entry.get("description"),
        ))
        logger.info("initializer: created prefix %s", prefix_str)

    db.commit()
