from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models import Balance, User as UserModel
from app.auth import get_current_user
from app.database import get_db

router = APIRouter(prefix="/api/v1/admin/balance", tags=["admin", "balance"])

@router.post("/deposit")
def deposit(user_id: str, ticker: str, amount: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "ADMIN":
        raise HTTPException(403, "Forbidden")
    balance = db.query(Balance).get((user_id, ticker))
    if not balance:
        balance = Balance(user_id=user_id, ticker=ticker, amount=0)
        db.add(balance)
    balance.amount += amount
    db.commit()
    return {"success": True}

@router.post("/withdraw")
def withdraw(user_id: str, ticker: str, amount: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "ADMIN":
        raise HTTPException(403, "Forbidden")
    balance = db.query(Balance).get((user_id, ticker))
    if not balance or balance.amount < amount:
        raise HTTPException(400, "Insufficient balance")
    balance.amount -= amount
    db.commit()
    return {"success": True}