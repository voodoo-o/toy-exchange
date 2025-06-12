from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models import LimitOrder, MarketOrder
from app.schemas import LimitOrderBody, MarketOrderBody, CreateOrderResponse, LimitOrder, MarketOrder, Ok
from app.auth import get_current_user
from app.database import get_db
import uuid
from datetime import datetime

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