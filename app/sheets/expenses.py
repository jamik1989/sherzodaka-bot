# app/sheets/expenses.py
from __future__ import annotations

from typing import Optional
import os
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import gspread
from google.oauth2.service_account import Credentials

from app.core.config import settings


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _get_client() -> Optional[gspread.Client]:
    creds_path = (settings.gsheet_creds_path or "").strip()
    if not creds_path:
        return None

    # relative path bo'lsa project rootdan ochib ko'ramiz
    if not os.path.isabs(creds_path):
        creds_path = os.path.join(os.getcwd(), creds_path)

    if not os.path.exists(creds_path):
        return None

    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    return gspread.authorize(creds)


def _tashkent_now_str() -> str:
    """
    Toshkent vaqti bilan joriy sana-vaqt.
    Format: YYYY-MM-DD HH:MM:SS
    """
    tz_name = getattr(settings, "timezone", "Asia/Tashkent")
    try:
        now = datetime.now(ZoneInfo(tz_name))
    except ZoneInfoNotFoundError:
        now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")


def append_expense_row(date_yyyy_mm_dd: str, title: str, amount: int) -> bool:
    """
    Sheetsga qator qo'shadi:
    Sana va vaqt (Toshkent) | Harajat nomi | Summa

    Hech narsa bo'lmasa False qaytaradi (bot ishlashini buzmaydi).
    """
    sheet_id = (settings.gsheet_id or "").strip()
    ws_name = (settings.gsheet_expenses_worksheet or "Harajatlar").strip()

    if not sheet_id:
        return False

    client = _get_client()
    if client is None:
        return False

    sh = client.open_by_key(sheet_id)

    try:
        ws = sh.worksheet(ws_name)
    except Exception:
        ws = sh.add_worksheet(title=ws_name, rows=1000, cols=10)

    # Header yo'q bo'lsa qo'yamiz
    try:
        header = ws.row_values(1)
        if not header or header[:3] != ["Sana va vaqt", "Harajat nomi", "Summa"]:
            ws.update("A1:C1", [["Sana va vaqt", "Harajat nomi", "Summa"]])
    except Exception:
        # header qo'yolmasa ham appendni sinab ko'ramiz
        pass

    tashkent_datetime = _tashkent_now_str()

    ws.append_row(
        [tashkent_datetime, title, int(amount)],
        value_input_option="USER_ENTERED"
    )

    return True