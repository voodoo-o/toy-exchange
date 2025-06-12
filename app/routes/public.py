from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models import User as UserModel, Instrument
from app.schemas import NewUser, User, Instrument as InstrumentSchema
from app.auth import get_current_user
from app.database import get_db
import uuid

router = APIRouter(prefix="/api/v1/public", tags=["public"])

@router.post("/register", response_model=User)
def register(user_in: NewUser, db: Session = Depends(get_db)):
    api_key = f"key-{uuid.uuid4()}"
    user = UserModel(name=user_in.name, api_key=api_key, role="USER")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.get("/instrument", response_model=list[InstrumentSchema])
def list_instruments(db: Session = Depends(get_db)):
    return db.query(Instrument).all()