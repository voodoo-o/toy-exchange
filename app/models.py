from sqlalchemy import Column, String, Integer, ForeignKey, Enum as SQLEnum, DateTime
from sqlalchemy.orm import relationship, declarative_base
import uuid
from datetime import datetime
from enum import Enum

Base = declarative_base()

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

class User(Base):
    __tablename__ = 'users'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    api_key = Column(String, unique=True, nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.USER)

class Balance(Base):
    __tablename__ = 'balances'
    user_id = Column(String, ForeignKey('users.id'), primary_key=True)
    ticker = Column(String, ForeignKey('instruments.ticker'), primary_key=True)
    amount = Column(Integer, default=0)

    user = relationship("User")
    instrument = relationship("Instrument")

class Instrument(Base):
    __tablename__ = 'instruments'
    name = Column(String, nullable=False)
    ticker = Column(String, primary_key=True)

class LimitOrderBody:
    direction = Column(SQLEnum(Direction))
    ticker = Column(String)
    qty = Column(Integer)
    price = Column(Integer)

class MarketOrderBody:
    direction = Column(SQLEnum(Direction))
    ticker = Column(String)
    qty = Column(Integer)

class LimitOrder(Base, LimitOrderBody):
    __tablename__ = 'limit_orders'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    status = Column(SQLEnum(OrderStatus))
    user_id = Column(String, ForeignKey('users.id'))
    timestamp = Column(DateTime, default=datetime.utcnow)
    filled = Column(Integer, default=0)

class MarketOrder(Base, MarketOrderBody):
    __tablename__ = 'market_orders'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    status = Column(SQLEnum(OrderStatus))
    user_id = Column(String, ForeignKey('users.id'))
    timestamp = Column(DateTime, default=datetime.utcnow)