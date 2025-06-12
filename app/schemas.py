from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime
import uuid

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

class NewUser(BaseModel):
    name: str = Field(..., min_length=3)

class User(BaseModel):
    id: uuid.UUID
    name: str
    role: UserRole
    api_key: str

class Instrument(BaseModel):
    name: str
    ticker: str = Field(..., pattern=r"^[A-Z]{2,10}$")

class Level(BaseModel):
    price: int
    qty: int

class L2OrderBook(BaseModel):
    bid_levels: List[Level]
    ask_levels: List[Level]

class LimitOrderBody(BaseModel):
    direction: Direction
    ticker: str
    qty: int = Field(..., ge=1)
    price: int = Field(..., gt=0)

class MarketOrderBody(BaseModel):
    direction: Direction
    ticker: str
    qty: int = Field(..., ge=1)

class LimitOrder(LimitOrderBody):
    id: uuid.UUID
    status: OrderStatus
    user_id: uuid.UUID
    timestamp: datetime
    filled: int = 0

class MarketOrder(MarketOrderBody):
    id: uuid.UUID
    status: OrderStatus
    user_id: uuid.UUID
    timestamp: datetime

class CreateOrderResponse(BaseModel):
    success: bool = True
    order_id: uuid.UUID

class Ok(BaseModel):
    success: bool = True

class Transaction(BaseModel):
    id: uuid.UUID
    ticker: str
    amount: int
    price: int
    timestamp: datetime
    buyer_id: uuid.UUID
    seller_id: uuid.UUID

class ValidationError(BaseModel):
    loc: list
    msg: str
    type: str

class HTTPValidationError(BaseModel):
    detail: List[ValidationError]