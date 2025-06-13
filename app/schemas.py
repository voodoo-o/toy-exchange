from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
from datetime import datetime, timezone

class MyBaseModel(BaseModel):
    class Config:
        json_encoders = {
            datetime: lambda v: v.astimezone(timezone.utc).isoformat()
        }

class UserRole(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"

class OrderStatus(str, Enum):
    NEW = "NEW"
    EXECUTED = "EXECUTED"
    PARTIALLY_EXECUTED = "PARTIALLY_EXECUTED"
    CANCELLED = "CANCELLED"

class Direction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class NewUser(MyBaseModel):
    name: str = Field(..., min_length=3)

class User(MyBaseModel):
    id: str
    name: str
    role: UserRole
    api_key: str

class Instrument(MyBaseModel):
    name: str
    ticker: str = Field(..., pattern=r"^[A-Z]{2,10}$")

class Level(MyBaseModel):
    price: int
    qty: int

class L2OrderBook(MyBaseModel):
    bid_levels: List[Level]
    ask_levels: List[Level]

class LimitOrderBody(MyBaseModel):
    direction: Direction
    ticker: str
    qty: int = Field(..., ge=1)
    price: int = Field(..., gt=0)

class MarketOrderBody(MyBaseModel):
    direction: Direction
    ticker: str
    qty: int = Field(..., ge=1)

class LimitOrder(MyBaseModel):
    id: str
    status: OrderStatus
    user_id: str
    timestamp: datetime
    body: LimitOrderBody
    filled: int = 0

class MarketOrder(MyBaseModel):
    id: str
    status: OrderStatus
    user_id: str
    timestamp: datetime
    body: MarketOrderBody

class CreateOrderResponse(MyBaseModel):
    success: bool = True
    order_id: str

class Ok(MyBaseModel):
    success: bool = True

class Transaction(MyBaseModel):
    ticker: str
    amount: int
    price: int
    timestamp: datetime

class ValidationError(MyBaseModel):
    loc: list
    msg: str
    type: str

class HTTPValidationError(MyBaseModel):
    detail: List[ValidationError] 