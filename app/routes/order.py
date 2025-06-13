from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas import LimitOrderBody, MarketOrderBody, CreateOrderResponse, LimitOrder, MarketOrder, Ok
from app.models import LimitOrder as LimitOrderModel, MarketOrder as MarketOrderModel, OrderStatus, Balance
from app.auth import get_current_user
from app.database import get_db
import uuid
from datetime import datetime, timezone
from typing import List, Union

router = APIRouter()

# Вспомогательная функция для проверки баланса
def get_balance(db, user_id, ticker):
    bal = db.query(Balance).get((user_id, ticker))
    return bal.amount if bal else 0

def update_balance(db, user_id, ticker, delta):
    bal = db.query(Balance).get((user_id, ticker))
    if not bal:
        bal = Balance(user_id=user_id, ticker=ticker, amount=0)
        db.add(bal)
    bal.amount += delta
    if bal.amount < 0:
        raise HTTPException(400, "Insufficient balance")

# Исполнение лимитных ордеров (упрощённо)
def match_limit_order(db, order):
    # BUY ищет SELL, SELL ищет BUY
    if order.direction == "BUY":
        counter_orders = db.query(LimitOrderModel).filter(
            LimitOrderModel.ticker == order.ticker,
            LimitOrderModel.direction == "SELL",
            LimitOrderModel.status == OrderStatus.NEW,
            LimitOrderModel.price <= order.price
        ).order_by(LimitOrderModel.price, LimitOrderModel.timestamp).all()
    else:
        counter_orders = db.query(LimitOrderModel).filter(
            LimitOrderModel.ticker == order.ticker,
            LimitOrderModel.direction == "BUY",
            LimitOrderModel.status == OrderStatus.NEW,
            LimitOrderModel.price >= order.price
        ).order_by(-LimitOrderModel.price, LimitOrderModel.timestamp).all()
    qty_left = order.qty - order.filled
    for counter in counter_orders:
        counter_qty_left = counter.qty - counter.filled
        trade_qty = min(qty_left, counter_qty_left)
        if trade_qty <= 0:
            continue
        order.filled += trade_qty
        counter.filled += trade_qty
        # Обновить балансы (упрощённо)
        if order.direction == "BUY":
            update_balance(db, order.user_id, "RUB", -trade_qty * counter.price)
            update_balance(db, order.user_id, order.ticker, trade_qty)
            update_balance(db, counter.user_id, "RUB", trade_qty * counter.price)
            update_balance(db, counter.user_id, order.ticker, -trade_qty)
        else:
            update_balance(db, order.user_id, "RUB", trade_qty * order.price)
            update_balance(db, order.user_id, order.ticker, -trade_qty)
            update_balance(db, counter.user_id, "RUB", -trade_qty * order.price)
            update_balance(db, counter.user_id, order.ticker, trade_qty)
        qty_left -= trade_qty
        if counter.filled == counter.qty:
            counter.status = OrderStatus.EXECUTED
        else:
            counter.status = OrderStatus.PARTIALLY_EXECUTED
        if qty_left == 0:
            break
    if order.filled == order.qty:
        order.status = OrderStatus.EXECUTED
    elif order.filled > 0:
        order.status = OrderStatus.PARTIALLY_EXECUTED
    else:
        order.status = OrderStatus.NEW
    return order

@router.post("", response_model=CreateOrderResponse)
def create_order(
    body: Union[LimitOrderBody, MarketOrderBody],
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    order_id = str(uuid.uuid4())
    # Проверка баланса для BUY
    if body.direction == "BUY":
        if get_balance(db, current_user.id, "RUB") < body.qty * (getattr(body, 'price', 1)):
            raise HTTPException(400, "Insufficient balance for buy")
    # Проверка баланса для SELL
    if body.direction == "SELL":
        if get_balance(db, current_user.id, body.ticker) < body.qty:
            raise HTTPException(400, "Insufficient balance for sell")
    if isinstance(body, LimitOrderBody):
        order = LimitOrderModel(
            id=order_id,
            status=OrderStatus.NEW,
            user_id=current_user.id,
            timestamp=datetime.now(timezone.utc),
            direction=body.direction,
            ticker=body.ticker,
            qty=body.qty,
            price=body.price,
            filled=0
        )
        db.add(order)
        db.flush()
        match_limit_order(db, order)
        db.commit()
        # Если ордер не исполнен вообще, он остаётся в стакане
        if order.filled == 0:
            pass
    else:
        # Для MarketOrder выбрасываем ошибку, если нет встречных заявок
        if body.direction == "BUY":
            counter_orders = db.query(LimitOrderModel).filter(
                LimitOrderModel.ticker == body.ticker,
                LimitOrderModel.direction == "SELL",
                LimitOrderModel.status == OrderStatus.NEW
            ).order_by(LimitOrderModel.price, LimitOrderModel.timestamp).all()
        else:
            counter_orders = db.query(LimitOrderModel).filter(
                LimitOrderModel.ticker == body.ticker,
                LimitOrderModel.direction == "BUY",
                LimitOrderModel.status == OrderStatus.NEW
            ).order_by(-LimitOrderModel.price, LimitOrderModel.timestamp).all()
        if not counter_orders:
            raise HTTPException(400, "No counter orders for market order")
        order = MarketOrderModel(
            id=order_id,
            status=OrderStatus.NEW,
            user_id=current_user.id,
            timestamp=datetime.now(timezone.utc),
            direction=body.direction,
            ticker=body.ticker,
            qty=body.qty
        )
        db.add(order)
        db.flush()
        # Исполнить market order полностью по встречным заявкам
        qty_left = order.qty
        for counter in counter_orders:
            counter_qty_left = counter.qty - counter.filled
            trade_qty = min(qty_left, counter_qty_left)
            if trade_qty <= 0:
                continue
            if body.direction == "BUY":
                update_balance(db, current_user.id, "RUB", -trade_qty * counter.price)
                update_balance(db, current_user.id, body.ticker, trade_qty)
                update_balance(db, counter.user_id, "RUB", trade_qty * counter.price)
                update_balance(db, counter.user_id, body.ticker, -trade_qty)
            else:
                update_balance(db, current_user.id, "RUB", trade_qty * counter.price)
                update_balance(db, current_user.id, body.ticker, -trade_qty)
                update_balance(db, counter.user_id, "RUB", -trade_qty * counter.price)
                update_balance(db, counter.user_id, body.ticker, trade_qty)
            qty_left -= trade_qty
            counter.filled += trade_qty
            if counter.filled == counter.qty:
                counter.status = OrderStatus.EXECUTED
            else:
                counter.status = OrderStatus.PARTIALLY_EXECUTED
            if qty_left == 0:
                break
        if qty_left > 0:
            raise HTTPException(400, "Market order not fully executed")
        order.status = OrderStatus.EXECUTED
        db.commit()
        return {"success": True, "order_id": order_id}
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
    # Нельзя отменить исполненный ордер
    if lo and lo.status != OrderStatus.NEW:
        raise HTTPException(400, "Order already executed or cancelled")
    if mo and mo.status != OrderStatus.NEW:
        raise HTTPException(400, "Order already executed or cancelled")
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