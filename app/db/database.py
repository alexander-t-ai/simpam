import os
import sqlite3

from sqlalchemy import create_engine, event, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////data/ipam.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _record):
    if isinstance(dbapi_conn, sqlite3.Connection):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables, dropping all first if the schema is out of date."""
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    ip_cols = {c["name"] for c in inspector.get_columns("ip_addresses")} if "ip_addresses" in existing else set()
    needs_migration = (
        "roles" not in existing
        or ("prefixes" in existing and "role_id" not in {c["name"] for c in inspector.get_columns("prefixes")})
        or ("ip_addresses" in existing and "role_id" in ip_cols)
    )
    if needs_migration:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
