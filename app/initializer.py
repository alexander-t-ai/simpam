import logging
import os

import netaddr
import yaml
from sqlalchemy.orm import Session

from app.db.models import Prefix, Role

INITIALIZERS_DIR = os.getenv("INITIALIZERS_DIR", "/initializers")
logger = logging.getLogger("ipam")


class InitializerLoader:
    def __init__(self, db: Session, initializers_dir: str = INITIALIZERS_DIR):
        self.db = db
        self.initializers_dir = initializers_dir

    def run(self) -> None:
        self._load_roles()
        self._load_prefixes()

    def _load_roles(self) -> None:
        path = os.path.join(self.initializers_dir, "prefix_vlan_roles.yml")
        try:
            with open(path) as f:
                entries = yaml.safe_load(f) or []
        except FileNotFoundError:
            return

        for entry in entries:
            name = entry.get("name")
            if not name:
                continue
            if self.db.query(Role).filter(Role.name == name).first():
                continue
            self.db.add(Role(name=name, description=entry.get("description")))
            logger.info("initializer: created role '%s'", name)

        self.db.commit()

    def _load_prefixes(self) -> None:
        path = os.path.join(self.initializers_dir, "prefixes.yml")
        try:
            with open(path) as f:
                entries = yaml.safe_load(f) or []
        except FileNotFoundError:
            return

        for entry in entries:
            prefix_str = entry.get("prefix")
            if not prefix_str:
                continue
            if self.db.query(Prefix).filter(Prefix.prefix == prefix_str).first():
                continue

            role_id = None
            role_name = entry.get("role")
            if role_name:
                role_obj = self.db.query(Role).filter(Role.name == role_name).first()
                if role_obj:
                    role_id = role_obj.id
                else:
                    logger.warning("initializer: role '%s' not found for prefix %s, skipping role", role_name, prefix_str)

            try:
                net = netaddr.IPNetwork(prefix_str)
            except (netaddr.AddrFormatError, ValueError):
                logger.warning("initializer: invalid prefix '%s', skipping", prefix_str)
                continue

            self.db.add(Prefix(
                prefix=prefix_str,
                family=net.version,
                status=entry.get("status", "active"),
                role_id=role_id,
                description=entry.get("description"),
            ))
            logger.info("initializer: created prefix %s", prefix_str)

        self.db.commit()


def run(db: Session) -> None:
    InitializerLoader(db).run()
