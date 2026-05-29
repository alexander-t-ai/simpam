from fastapi import APIRouter, Depends, HTTPException
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
            db.query(model).delete()
        db.commit()
        if init_method:
            getattr(loader, init_method)()
    else:
        db.query(IPAddress).delete()
        db.query(Prefix).delete()
        db.query(Role).delete()
        db.commit()
        loader.run()
