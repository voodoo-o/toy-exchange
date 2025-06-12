from fastapi import FastAPI
from app.routes import public, order, admin_balance, balance, admin_instrument, admin_user

app = FastAPI(title="Toy Exchange", version="0.1.0")

app.include_router(public.router, prefix="/api/v1/public")
app.include_router(order.router, prefix="/api/v1/order")
app.include_router(admin_balance.router, prefix="/api/v1/admin/balance")
app.include_router(balance.router, prefix="/api/v1/balance")
app.include_router(admin_instrument.router, prefix="/api/v1/admin/instrument")
app.include_router(admin_user.router, prefix="/api/v1/admin/user")