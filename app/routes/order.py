from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models import LimitOrder, MarketOrder, Transaction
from app.schemas import LimitOrderBody, MarketOrderBody, CreateOrderResponse, LimitOrder, MarketOrder, Ok, L2OrderBook, Level, Transaction as TransactionSchema
from app.auth import get_current_user
from app.database import get_db
import uuid
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List

router = APIRouter(prefix="/api/v1/order", tags=["order"])

@router.post("", response_model=CreateOrderResponse)
def create_order(
    body: LimitOrderBody | MarketOrderBody,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    order_id = str(uuid.uuid4())
    if isinstance(body, LimitOrderBody):
        order = LimitOrder(
            id=order_id,
            status="NEW",
            user_id=current_user.id,
            timestamp=datetime.utcnow(),
            direction=body.direction,
            ticker=body.ticker,
            qty=body.qty,
            price=body.price
        )
    else:
        order = MarketOrder(
            id=order_id,
            status="NEW",
            user_id=current_user.id,
            timestamp=datetime.utcnow(),
            direction=body.direction,
            ticker=body.ticker,
            qty=body.qty
        )
    db.add(order)
    db.commit()
    return {"success": True, "order_id": order_id}

@router.get("/{order_id}", response_model=LimitOrder | MarketOrder)
def get_order(order_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    lo = db.query(LimitOrder).get(order_id)
    mo = db.query(MarketOrder).get(order_id)
    if not lo and not mo:
        raise HTTPException(404, "Order not found")
    return lo or mo

@router.delete("/{order_id}", response_model=Ok)
def cancel_order(order_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    lo = db.query(LimitOrder).get(order_id)
    mo = db.query(MarketOrder).get(order_id)
    if not lo and not mo:
        raise HTTPException(404, "Order not found")
    if lo:
        lo.status = "CANCELLED"
    if mo:
        mo.status = "CANCELLED"
    db.commit()
    return {"success": True}

@router.get("", response_model=list[LimitOrder | MarketOrder])
def list_orders(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    los = db.query(LimitOrder).filter(LimitOrder.user_id == current_user.id).all()
    mos = db.query(MarketOrder).filter(MarketOrder.user_id == current_user.id).all()
    return los + mos

@router.get("/book/{ticker}", response_model=L2OrderBook)
def get_order_book(ticker: str, db: Session = Depends(get_db)):
    active_orders = db.query(LimitOrder).filter(
        LimitOrder.ticker == ticker,
        LimitOrder.status == "NEW"
    ).all()
    
    bids = defaultdict(int)
    asks = defaultdict(int)
    
    for order in active_orders:
        if order.direction == "BUY":
            bids[order.price] += order.qty - order.filled
        else:
            asks[order.price] += order.qty - order.filled
    
    bid_levels = [Level(price=price, qty=qty) for price, qty in sorted(bids.items(), reverse=True)]
    ask_levels = [Level(price=price, qty=qty) for price, qty in sorted(asks.items())]
    
    return L2OrderBook(bid_levels=bid_levels, ask_levels=ask_levels)

@router.get("/history/{ticker}", response_model=List[TransactionSchema])
def get_transaction_history(
    ticker: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
    days: int = 7
):
    start_date = datetime.utcnow() - timedelta(days=days)
    transactions = db.query(Transaction).filter(
        Transaction.ticker == ticker,
        Transaction.timestamp >= start_date,
        (Transaction.buyer_id == current_user.id) | (Transaction.seller_id == current_user.id)
    ).order_by(Transaction.timestamp.desc()).all()
    
    return transactions