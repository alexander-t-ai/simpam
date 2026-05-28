from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import IPAddress, Prefix

router = APIRouter(tags=["reset"])


@router.post("/reset/", status_code=204)
def reset_database(db: Session = Depends(get_db)):
    """Truncate IP addresses and prefixes. Used by integration tests."""
    db.query(IPAddress).delete()
    db.query(Prefix).delete()
    db.commit()
