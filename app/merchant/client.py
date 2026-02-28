# app/merchant/client.py
import httpx
from typing import Any, Dict, Optional

class TwoPayClient:
    def __init__(self, base_url: str, token: str, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.token = token.strip()
        self.timeout = timeout

    def _headers(self) -> Dict[str, str]:
        return {
            "Accept": "application/json",
            "Authorization": f"Token {self.token}",
        }

    async def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(url, headers=self._headers(), params=params)
            r.raise_for_status()
            return r.json()