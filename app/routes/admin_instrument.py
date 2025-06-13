from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models import Instrument as InstrumentModel
from app.schemas import Instrument, Ok
from app.auth import get_current_user
from app.database import get_db

router = APIRouter()

@router.post("", response_model=Ok)
def add_instrument(instrument: Instrument, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    inst = InstrumentModel(**instrument.dict())
    db.add(inst)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, "Instrument already exists")
    return {"success": True}

@router.delete("/{ticker}", response_model=Ok)
def delete_instrument(ticker: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    inst = db.query(InstrumentModel).get(ticker)
    if not inst:
        raise HTTPException(404, "Instrument not found")
    db.delete(inst)
    db.commit()
    return {"success": True} 