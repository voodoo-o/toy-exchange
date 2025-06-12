from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.models import Balance
from app.auth import get_current_user
from app.database import get_db

router = APIRouter()

@router.get("")
def get_balances(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    balances = db.query(Balance).filter(Balance.user_id == current_user.id).all()
    return {b.ticker: b.amount for b in balances} 