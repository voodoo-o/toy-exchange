from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models import Instrument
from app.schemas import Instrument as InstrumentSchema
from app.auth import get_current_user
from app.database import get_db

router = APIRouter(prefix="/api/v1/admin/instrument", tags=["admin"])

@router.post("")
def add_instrument(instrument: InstrumentSchema, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "ADMIN":
        raise HTTPException(403, "Forbidden")
    inst = Instrument(**instrument.dict())
    db.add(inst)
    db.commit()
    return {"success": True}

@router.delete("/{ticker}")
def delete_instrument(ticker: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "ADMIN":
        raise HTTPException(403, "Forbidden")
    inst = db.query(Instrument).get(ticker)
    if not inst:
        raise HTTPException(404, "Instrument not found")
    db.delete(inst)
    db.commit()
    return {"success": True}