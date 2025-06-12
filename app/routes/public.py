from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas import NewUser, User, Instrument, L2OrderBook, Level, Transaction
from app.models import User as UserModel, Instrument as InstrumentModel, LimitOrder, Transaction as TransactionModel
from app.database import get_db
import uuid
from collections import defaultdict
from typing import List

router = APIRouter()

@router.post("/register", response_model=User)
def register(user_in: NewUser, db: Session = Depends(get_db)):
    api_key = f"key-{uuid.uuid4()}"
    user = UserModel(id=str(uuid.uuid4()), name=user_in.name, api_key=api_key, role="USER")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.get("/instrument", response_model=List[Instrument])
def list_instruments(db: Session = Depends(get_db)):
    return db.query(InstrumentModel).all()

@router.get("/orderbook/{ticker}", response_model=L2OrderBook)
def get_orderbook(ticker: str, limit: int = 10, db: Session = Depends(get_db)):
    if limit > 25:
        limit = 25
    active_orders = db.query(LimitOrder).filter(LimitOrder.ticker == ticker, LimitOrder.status == "NEW").all()
    bids = defaultdict(int)
    asks = defaultdict(int)
    for order in active_orders:
        if order.direction == "BUY":
            bids[order.price] += order.qty - order.filled
        else:
            asks[order.price] += order.qty - order.filled
    bid_levels = [Level(price=price, qty=qty) for price, qty in sorted(bids.items(), reverse=True)[:limit]]
    ask_levels = [Level(price=price, qty=qty) for price, qty in sorted(asks.items())[:limit]]
    return L2OrderBook(bid_levels=bid_levels, ask_levels=ask_levels)

@router.get("/transactions/{ticker}", response_model=List[Transaction])
def get_transaction_history(ticker: str, limit: int = 10, db: Session = Depends(get_db)):
    if limit > 100:
        limit = 100
    transactions = db.query(TransactionModel).filter(TransactionModel.ticker == ticker).order_by(TransactionModel.timestamp.desc()).limit(limit).all()
    return transactions 