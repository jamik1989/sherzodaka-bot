# app/merchant/service.py
from __future__ import annotations

from typing import Any, Dict, Optional, List, Tuple
from app.merchant.client import TwoPayClient

# Network’da ko‘ringan endpointlar
DASHBOARD_PATH = "/api/merchant/dashboard/"
ONLINE_LIST_PATH = "/api/merchant/transactions/online-list/"

# Naqd endpoint variantlari (sizda cash-list ishlayapti)
CASH_ENDPOINT_CANDIDATES: List[str] = [
    "/api/merchant/transactions/cash-list/",
    "/api/merchant/transactions/cashin-list/",
    "/api/merchant/transactions/cash/",
]


def _extract_items(data: Any) -> list[dict]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if isinstance(data.get("results"), list):
            return data["results"]
        if isinstance(data.get("data"), list):
            return data["data"]
    return []


def _day_range_dt(date_yyyy_mm_dd: str) -> tuple[str, str]:
    return f"{date_yyyy_mm_dd} 00:00:00", f"{date_yyyy_mm_dd} 23:59:59"


async def fetch_dashboard(client: TwoPayClient) -> dict:
    """
    Dashboard’dagi bugungi/kecagi/haftalik/oylik sumlar shu yerdan keladi.
    """
    data = await client.get(DASHBOARD_PATH, params=None)
    if isinstance(data, dict):
        return data
    return {"raw": data}


async def _fetch_list(
    client: TwoPayClient,
    path: str,
    page: int,
    page_size: int,
    after: Optional[str] = None,
    before: Optional[str] = None,
    status: Optional[str] = None,
) -> Any:
    params: Dict[str, Any] = {"page": page, "page_size": page_size}
    if after:
        params["after"] = after
    if before:
        params["before"] = before
    if status:
        params["status"] = status
    return await client.get(path, params=params)


async def fetch_all_pages(
    client: TwoPayClient,
    path: str,
    after: Optional[str],
    before: Optional[str],
    status: Optional[str] = None,
    page_size: int = 200,
    max_pages: int = 200,
) -> list[dict]:
    all_items: list[dict] = []
    for page in range(1, max_pages + 1):
        data = await _fetch_list(
            client=client,
            path=path,
            page=page,
            page_size=page_size,
            after=after,
            before=before,
            status=status,
        )
        items = _extract_items(data)
        if not items:
            break
        all_items.extend(items)
        if len(items) < page_size:
            break
    return all_items


async def _try_day_query(
    client: TwoPayClient,
    path: str,
    date_yyyy_mm_dd: str,
    status: str = "finished",
) -> list[dict]:
    after_dt, before_dt = _day_range_dt(date_yyyy_mm_dd)
    try:
        return await fetch_all_pages(client, path, after=after_dt, before=before_dt, status=status)
    except Exception:
        return await fetch_all_pages(client, path, after=date_yyyy_mm_dd, before=date_yyyy_mm_dd, status=status)


async def fetch_online_transactions(
    client: TwoPayClient,
    page: int = 1,
    page_size: int = 10,
    after: Optional[str] = None,
    before: Optional[str] = None,
    status: Optional[str] = None,
) -> Any:
    params: Dict[str, Any] = {"page": page, "page_size": page_size}
    if after:
        params["after"] = after
    if before:
        params["before"] = before
    if status:
        params["status"] = status
    return await client.get(ONLINE_LIST_PATH, params=params)


async def fetch_click_transactions(client: TwoPayClient, date_yyyy_mm_dd: str) -> list[dict]:
    return await _try_day_query(client, ONLINE_LIST_PATH, date_yyyy_mm_dd, status="finished")


async def fetch_cash_transactions(client: TwoPayClient, date_yyyy_mm_dd: str) -> Tuple[Optional[list[dict]], Optional[str]]:
    for path in CASH_ENDPOINT_CANDIDATES:
        try:
            items = await _try_day_query(client, path, date_yyyy_mm_dd, status="finished")
            return items, path
        except Exception:
            continue
    return None, None