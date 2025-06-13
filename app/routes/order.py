from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.schemas import LimitOrderBody, MarketOrderBody, CreateOrderResponse, LimitOrder, MarketOrder, Ok
from app.models import LimitOrder as LimitOrderModel, MarketOrder as MarketOrderModel, OrderStatus, Balance, Instrument as InstrumentModel, Transaction as TransactionModel
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
        if delta < 0:
            raise HTTPException(400, "Insufficient balance")
        bal = Balance(user_id=user_id, ticker=ticker, amount=0)
        db.add(bal)
    # Проверяем, что после изменения баланс не станет отрицательным
    if bal.amount + delta < 0:
        raise HTTPException(400, "Insufficient balance")
    bal.amount += delta
    db.flush()  # Немедленно применяем изменения, чтобы избежать конфликтов

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
        ).order_by(desc(LimitOrderModel.price), LimitOrderModel.timestamp).all()
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
            # Создать сделку
            db.add(TransactionModel(
                id=str(uuid.uuid4()),
                ticker=order.ticker,
                amount=trade_qty,
                price=counter.price,
                timestamp=datetime.now(timezone.utc),
                buyer_id=order.user_id,
                seller_id=counter.user_id
            ))
        else:
            update_balance(db, order.user_id, "RUB", trade_qty * order.price)
            update_balance(db, order.user_id, order.ticker, -trade_qty)
            update_balance(db, counter.user_id, "RUB", -trade_qty * order.price)
            update_balance(db, counter.user_id, order.ticker, trade_qty)
            # Создать сделку
            db.add(TransactionModel(
                id=str(uuid.uuid4()),
                ticker=order.ticker,
                amount=trade_qty,
                price=order.price,
                timestamp=datetime.now(timezone.utc),
                buyer_id=counter.user_id,
                seller_id=order.user_id
            ))
        db.flush()  # Немедленно применяем изменения после каждого trade
        qty_left -= trade_qty
        if counter.filled == counter.qty:
            counter.status = OrderStatus.EXECUTED
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
async def create_order(
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        body_json = await request.json()
        # Определяем тип ордера по наличию поля price
        if "price" in body_json:
            body = LimitOrderBody(**body_json)
            is_limit = True
        else:
            body = MarketOrderBody(**body_json)
            is_limit = False
        order_id = str(uuid.uuid4())
        # Проверка существования инструмента
        instrument = db.query(InstrumentModel).get(body.ticker)
        if not instrument:
            raise HTTPException(400, "Instrument not found")
        # Проверка на корректность qty и price
        if (is_limit and (body.qty <= 0 or body.price <= 0)) or (not is_limit and body.qty <= 0):
            raise HTTPException(400, "Invalid qty or price")
        # Проверка баланса и встречных заявок ДО создания ордера и изменения баланса
        if is_limit:
            if body.direction == "BUY":
                if get_balance(db, current_user.id, "RUB") < body.qty * body.price:
                    raise HTTPException(400, "Insufficient balance for buy")
            if body.direction == "SELL":
                if get_balance(db, current_user.id, body.ticker) < body.qty:
                    raise HTTPException(400, "Insufficient balance for sell")
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
            if order.filled == 0:
                pass
        else:
            if body.direction == "BUY":
                counter_orders = db.query(LimitOrderModel).filter(
                    LimitOrderModel.ticker == body.ticker,
                    LimitOrderModel.direction == "SELL",
                    LimitOrderModel.status == OrderStatus.NEW
                ).order_by(LimitOrderModel.price, LimitOrderModel.timestamp).all()
                if not counter_orders:
                    raise HTTPException(400, "No counter orders for market order")
                qty_left = body.qty
                total_rub_needed = 0
                for counter in counter_orders:
                    counter_qty_left = counter.qty - counter.filled
                    trade_qty = min(qty_left, counter_qty_left)
                    if trade_qty <= 0:
                        continue
                    total_rub_needed += trade_qty * counter.price
                    qty_left -= trade_qty
                    if qty_left == 0:
                        break
                if qty_left > 0:
                    raise HTTPException(400, "Market order not fully executed")
                # Явная проверка баланса перед созданием ордера
                if get_balance(db, current_user.id, "RUB") < total_rub_needed:
                    raise HTTPException(400, "Insufficient balance for buy")
            else:
                counter_orders = db.query(LimitOrderModel).filter(
                    LimitOrderModel.ticker == body.ticker,
                    LimitOrderModel.direction == "BUY",
                    LimitOrderModel.status == OrderStatus.NEW
                ).order_by(-LimitOrderModel.price, LimitOrderModel.timestamp).all()
                if not counter_orders:
                    raise HTTPException(400, "No counter orders for market order")
                qty_left = body.qty
                for counter in counter_orders:
                    counter_qty_left = counter.qty - counter.filled
                    trade_qty = min(qty_left, counter_qty_left)
                    if trade_qty <= 0:
                        continue
                    qty_left -= trade_qty
                    if qty_left == 0:
                        break
                if qty_left > 0:
                    raise HTTPException(400, "Market order not fully executed")
                # Явная проверка баланса перед созданием ордера
                if get_balance(db, current_user.id, body.ticker) < body.qty:
                    raise HTTPException(400, "Insufficient balance for sell")
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
                    db.add(TransactionModel(
                        id=str(uuid.uuid4()),
                        ticker=body.ticker,
                        amount=trade_qty,
                        price=counter.price,
                        timestamp=datetime.now(timezone.utc),
                        buyer_id=current_user.id,
                        seller_id=counter.user_id
                    ))
                else:
                    update_balance(db, current_user.id, body.ticker, -trade_qty)
                    update_balance(db, current_user.id, "RUB", trade_qty * counter.price)
                    update_balance(db, counter.user_id, body.ticker, trade_qty)
                    update_balance(db, counter.user_id, "RUB", -trade_qty * counter.price)
                    db.add(TransactionModel(
                        id=str(uuid.uuid4()),
                        ticker=body.ticker,
                        amount=trade_qty,
                        price=counter.price,
                        timestamp=datetime.now(timezone.utc),
                        buyer_id=counter.user_id,
                        seller_id=current_user.id
                    ))
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
            print(f"[ORDER DEBUG] user_id={current_user.id} RUB_balance={get_balance(db, current_user.id, 'RUB')}")
            return {"success": True, "order_id": order_id}
        db.commit()
        return {"success": True, "order_id": order_id}
    except HTTPException as e:
        if e.status_code == 400:
            print(f"[ORDER 400] {e.detail}")
        raise e
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(400, f"Invalid order: {e}")

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
    if lo and lo.status in [OrderStatus.EXECUTED, OrderStatus.PARTIALLY_EXECUTED]:
        raise HTTPException(400, "Order already executed or cancelled")
    if mo and mo.status in [OrderStatus.EXECUTED, OrderStatus.PARTIALLY_EXECUTED]:
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