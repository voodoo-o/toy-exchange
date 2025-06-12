from fastapi import FastAPI
from app.routes import (
    public,
    order,
    admin_user,
    admin_instrument,
    admin_balance,
    balance
)

app = FastAPI(title="Toy Exchange", version="0.1.0")

app.include_router(public.router)
app.include_router(order.router)
app.include_router(admin_user.router)
app.include_router(admin_instrument.router)
app.include_router(admin_balance.router)
app.include_router(balance.router)

@app.on_event("startup")
def on_startup():
    from app.database import Base, engine
    Base.metadata.create_all(bind=engine)