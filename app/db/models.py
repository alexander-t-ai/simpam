from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)


class Prefix(Base):
    __tablename__ = "prefixes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    prefix: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    family: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, default="active", nullable=False)
    role_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("roles.id"), nullable=True)
    role: Mapped["Role | None"] = relationship("Role", lazy="selectin")
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class IPAddress(Base):
    __tablename__ = "ip_addresses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    address: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    family: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, default="active", nullable=False)
    role: Mapped[str | None] = mapped_column(String, nullable=True)
    dns_name: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
