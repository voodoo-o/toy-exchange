from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas import Ok
from app.models import Balance, User as UserModel, Instrument as InstrumentModel
from app.auth import get_current_user
from app.database import get_db
from pydantic import BaseModel, Field

class DepositBody(BaseModel):
    user_id: str
    ticker: str
    amount: int = Field(..., gt=0)

class WithdrawBody(BaseModel):
    user_id: str
    ticker: str
    amount: int = Field(..., gt=0)

router = APIRouter()

@router.post("/deposit", response_model=Ok)
def deposit(body: DepositBody, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(UserModel).get(body.user_id)
    if not user:
        raise HTTPException(404, "User not found")
    instrument = db.query(InstrumentModel).get(body.ticker)
    if not instrument:
        raise HTTPException(404, "Instrument not found")
    balance = db.query(Balance).get((body.user_id, body.ticker))
    if not balance:
        balance = Balance(user_id=body.user_id, ticker=body.ticker, amount=0)
        db.add(balance)
    balance.amount += body.amount
    db.commit()
    return {"success": True}

@router.post("/withdraw", response_model=Ok)
def withdraw(body: WithdrawBody, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(UserModel).get(body.user_id)
    if not user:
        raise HTTPException(404, "User not found")
    instrument = db.query(InstrumentModel).get(body.ticker)
    if not instrument:
        raise HTTPException(404, "Instrument not found")
    balance = db.query(Balance).get((body.user_id, body.ticker))
    if not balance or balance.amount < body.amount:
        raise HTTPException(400, "Insufficient balance")
    balance.amount -= body.amount
    db.commit()
    return {"success": True} 