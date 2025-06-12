from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.routes import (
    public,
    order,
    admin_user,
    admin_instrument,
    admin_balance,
    balance
)
from app.database import Base, engine
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Toy Exchange",
    description="API для биржи игрушек",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(public.router, prefix="/api/v1")
app.include_router(order.router, prefix="/api/v1")
app.include_router(admin_user.router, prefix="/api/v1/admin")
app.include_router(admin_instrument.router, prefix="/api/v1/admin")
app.include_router(admin_balance.router, prefix="/api/v1/admin")
app.include_router(balance.router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")
        raise

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    logger.error(f"HTTP error: {exc.detail}")
    return {"detail": exc.detail}, exc.status_code

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unexpected error: {str(exc)}")
    return {"detail": "Internal server error"}, 500

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    ssl_keyfile = os.getenv("SSL_KEYFILE")
    ssl_certfile = os.getenv("SSL_CERTFILE")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        ssl_keyfile=ssl_keyfile if ssl_keyfile else None,
        ssl_certfile=ssl_certfile if ssl_certfile else None
    )