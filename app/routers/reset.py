from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import IPAddress, Prefix, Role

router = APIRouter(tags=["reset"])

_ENTITY_MAP = {
    "ip-address": [IPAddress],
    "prefix": [Prefix],
    "role": [Role],
}


def _truncate(db: Session, model) -> None:
    db.query(model).delete()
    db.execute(text(f"DELETE FROM sqlite_sequence WHERE name = '{model.__tablename__}'"))


@router.post("/reset/", status_code=204)
def reset_database(entity: str | None = None, db: Session = Depends(get_db)):
    """Truncate tables. Pass ?entity=<ip-address|prefix|role> to clear one entity, or omit to clear all."""
    if entity is not None:
        models = _ENTITY_MAP.get(entity)
        if models is None:
            raise HTTPException(status_code=400, detail=f"Unknown entity '{entity}'. Must be one of: {', '.join(_ENTITY_MAP)}")
        for model in models:
            _truncate(db, model)
    else:
        _truncate(db, IPAddress)
        _truncate(db, Prefix)
        _truncate(db, Role)
    db.commit()
