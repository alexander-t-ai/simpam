from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import IPAddress, Prefix, Role
from app.initializer import InitializerLoader

router = APIRouter(tags=["reset"])

# Maps entity name → (models to truncate, initializer method name or None)
_ENTITY_MAP = {
    "ip-address": ([IPAddress], None),
    "prefix":     ([Prefix],    "load_prefixes"),
    "role":       ([Role],      "load_roles"),
}


def _truncate(db: Session, model) -> None:
    db.query(model).delete()
    db.execute(text("CREATE TABLE IF NOT EXISTS sqlite_sequence(name, seq)"))
    db.execute(text(f"DELETE FROM sqlite_sequence WHERE name = '{model.__tablename__}'"))


@router.post("/reset/", status_code=204)
def reset_database(entity: str | None = None, db: Session = Depends(get_db)):
    """Truncate tables and reload from initializer files."""
    loader = InitializerLoader(db)
    if entity is not None:
        entry = _ENTITY_MAP.get(entity)
        if entry is None:
            raise HTTPException(status_code=400, detail=f"Unknown entity '{entity}'. Must be one of: {', '.join(_ENTITY_MAP)}")
        models, init_method = entry
        for model in models:
            _truncate(db, model)
        db.commit()
        if init_method:
            getattr(loader, init_method)()
    else:
        _truncate(db, IPAddress)
        _truncate(db, Prefix)
        _truncate(db, Role)
        db.commit()
        loader.run()
