from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import IPAddress, Prefix, Role

router = APIRouter(tags=["reset"])

_ENTITY_MAP = {
    "ip-address": [IPAddress],
    "prefix": [Prefix],
    "role": [Role],
}


@router.post("/reset/", status_code=204)
def reset_database(entity: str | None = None, db: Session = Depends(get_db)):
    """Truncate tables. Pass ?entity=<ip-address|prefix|role> to clear one entity, or omit to clear all."""
    if entity is not None:
        models = _ENTITY_MAP.get(entity)
        if models is None:
            raise HTTPException(status_code=400, detail=f"Unknown entity '{entity}'. Must be one of: {', '.join(_ENTITY_MAP)}")
        for model in models:
            db.query(model).delete()
    else:
        db.query(IPAddress).delete()
        db.query(Prefix).delete()
        db.query(Role).delete()
    db.commit()
