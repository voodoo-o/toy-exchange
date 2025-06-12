from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas import LimitOrderBody, MarketOrderBody, CreateOrderResponse, LimitOrder, MarketOrder, Ok
from app.models import LimitOrder as LimitOrderModel, MarketOrder as MarketOrderModel, OrderStatus
from app.auth import get_current_user
from app.database import get_db
import uuid
from datetime import datetime
from typing import List, Union

router = APIRouter()

@router.post("", response_model=CreateOrderResponse)
def create_order(
    body: Union[LimitOrderBody, MarketOrderBody],
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    order_id = str(uuid.uuid4())
    if isinstance(body, LimitOrderBody):
        order = LimitOrderModel(
            id=order_id,
            status=OrderStatus.NEW,
            user_id=current_user.id,
            timestamp=datetime.utcnow(),
            direction=body.direction,
            ticker=body.ticker,
            qty=body.qty,
            price=body.price,
            filled=0
        )
    else:
        order = MarketOrderModel(
            id=order_id,
            status=OrderStatus.NEW,
            user_id=current_user.id,
            timestamp=datetime.utcnow(),
            direction=body.direction,
            ticker=body.ticker,
            qty=body.qty
        )
    db.add(order)
    db.commit()
    return {"success": True, "order_id": order_id}

@router.get("/{order_id}", response_model=Union[LimitOrder, MarketOrder])
def get_order(order_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    lo = db.query(LimitOrderModel).get(order_id)
    mo = db.query(MarketOrderModel).get(order_id)
    if not lo and not mo:
        raise HTTPException(404, "Order not found")
    if lo:
        return LimitOrder(
            id=lo.id,
            status=lo.status,
            user_id=lo.user_id,
            timestamp=lo.timestamp,
            filled=lo.filled,
            body=LimitOrderBody(
                direction=lo.direction,
                ticker=lo.ticker,
                qty=lo.qty,
                price=lo.price
            )
        )
    if mo:
        return MarketOrder(
            id=mo.id,
            status=mo.status,
            user_id=mo.user_id,
            timestamp=mo.timestamp,
            body=MarketOrderBody(
                direction=mo.direction,
                ticker=mo.ticker,
                qty=mo.qty
            )
        )

@router.delete("/{order_id}", response_model=Ok)
def cancel_order(order_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    lo = db.query(LimitOrderModel).get(order_id)
    mo = db.query(MarketOrderModel).get(order_id)
    if not lo and not mo:
        raise HTTPException(404, "Order not found")
    if lo:
        lo.status = OrderStatus.CANCELLED
    if mo:
        mo.status = OrderStatus.CANCELLED
    db.commit()
    return {"success": True}

@router.get("", response_model=List[Union[LimitOrder, MarketOrder]])
def list_orders(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    los = db.query(LimitOrderModel).filter(LimitOrderModel.user_id == current_user.id).all()
    mos = db.query(MarketOrderModel).filter(MarketOrderModel.user_id == current_user.id).all()
    result = []
    for lo in los:
        result.append(LimitOrder(
            id=lo.id,
            status=lo.status,
            user_id=lo.user_id,
            timestamp=lo.timestamp,
            filled=lo.filled,
            body=LimitOrderBody(
                direction=lo.direction,
                ticker=lo.ticker,
                qty=lo.qty,
                price=lo.price
            )
        ))
    for mo in mos:
        result.append(MarketOrder(
            id=mo.id,
            status=mo.status,
            user_id=mo.user_id,
            timestamp=mo.timestamp,
            body=MarketOrderBody(
                direction=mo.direction,
                ticker=mo.ticker,
                qty=mo.qty
            )
        ))
    return result 