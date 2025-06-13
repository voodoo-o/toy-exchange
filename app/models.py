from sqlalchemy import Column, String, Integer, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime, timezone
import enum

Base = declarative_base()

class UserRole(str, enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"

class User(Base):
    __tablename__ = 'users'
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.USER)
    api_key = Column(String, unique=True, nullable=False)
    balances = relationship("Balance", back_populates="user")

class Instrument(Base):
    __tablename__ = 'instruments'
    ticker = Column(String, primary_key=True)
    name = Column(String, nullable=False)

class Balance(Base):
    __tablename__ = 'balances'
    user_id = Column(String, ForeignKey('users.id'), primary_key=True)
    ticker = Column(String, ForeignKey('instruments.ticker'), primary_key=True)
    amount = Column(Integer, default=0)
    user = relationship("User", back_populates="balances")
    instrument = relationship("Instrument")

class OrderStatus(str, enum.Enum):
    NEW = "NEW"
    EXECUTED = "EXECUTED"
    PARTIALLY_EXECUTED = "PARTIALLY_EXECUTED"
    CANCELLED = "CANCELLED"

class Direction(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"

class LimitOrder(Base):
    __tablename__ = 'limit_orders'
    id = Column(String, primary_key=True)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.NEW)
    user_id = Column(String, ForeignKey('users.id'))
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    direction = Column(SQLEnum(Direction))
    ticker = Column(String, ForeignKey('instruments.ticker'))
    qty = Column(Integer)
    price = Column(Integer)
    filled = Column(Integer, default=0)

class MarketOrder(Base):
    __tablename__ = 'market_orders'
    id = Column(String, primary_key=True)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.NEW)
    user_id = Column(String, ForeignKey('users.id'))
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    direction = Column(SQLEnum(Direction))
    ticker = Column(String, ForeignKey('instruments.ticker'))
    qty = Column(Integer)

class Transaction(Base):
    __tablename__ = 'transactions'
    id = Column(String, primary_key=True)
    ticker = Column(String, ForeignKey('instruments.ticker'))
    amount = Column(Integer)
    price = Column(Integer)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    buyer_id = Column(String, ForeignKey('users.id'))
    seller_id = Column(String, ForeignKey('users.id')) 