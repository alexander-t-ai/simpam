from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Role
from app.exceptions import AlreadyExistsException


class RoleService:
    def __init__(self, db: Session):
        self.db = db

    def list_roles(self) -> list[Role]:
        return self.db.query(Role).order_by(Role.name).all()

    def create_role(self, name: str, description: str | None = None) -> Role:
        if self.db.query(Role).filter(Role.name == name).first():
            raise AlreadyExistsException("Role already exists")
        obj = Role(name=name, description=description)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj


def get_role_service(db: Session = Depends(get_db)) -> RoleService:
    return RoleService(db)
