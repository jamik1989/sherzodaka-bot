from fastapi import APIRouter, Request

router = APIRouter()

@router.post("/webhook")
async def merchant_webhook(request: Request):
    payload = await request.json()
    # TODO: verify signature + process payment status
    return {"ok": True, "received": payload}
