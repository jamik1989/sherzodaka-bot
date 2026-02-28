from fastapi import FastAPI
from app.routers.health import router as health_router
from app.merchant.webhook_router import router as merchant_webhook_router

app = FastAPI(title="Sherzodaka Merchant + Bot")

app.include_router(health_router)
app.include_router(merchant_webhook_router, prefix="/merchant", tags=["merchant"])
