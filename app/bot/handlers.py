# app/bot/handlers.py
from __future__ import annotations

import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Any

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.core.config import settings
from app.merchant.client import TwoPayClient
from app.merchant.service import (
    fetch_dashboard,
    fetch_online_transactions,
    fetch_click_transactions,
    fetch_cash_transactions,
)
from app.expenses.db import init_db, add_expense, list_expenses, sum_expenses, set_meta

# ✅ NEW: Sheets append helper
from app.sheets.expenses import append_expense_row

router = Router()

# ---- FSM ----
class ExpenseFlow(StatesGroup):
    title = State()
    amount = State()


# ---- Helpers ----
def _fmt_sum(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def _to_int(v: Any) -> int:
    try:
        return int(float(v))
    except Exception:
        return 0


def sum_amount(items: list[dict]) -> int:
    total = 0
    for x in items:
        total += _to_int(x.get("amount", 0))
    return total


def _tz_now() -> datetime:
    tz_name = getattr(settings, "timezone", "Asia/Tashkent")
    try:
        return datetime.now(ZoneInfo(tz_name))
    except ZoneInfoNotFoundError:
        return datetime.now()


def today_str() -> str:
    return _tz_now().strftime("%Y-%m-%d")


def format_ddmmyyyy(date_yyyy_mm_dd: str) -> str:
    try:
        return datetime.strptime(date_yyyy_mm_dd, "%Y-%m-%d").strftime("%d.%m.%Y")
    except Exception:
        return date_yyyy_mm_dd


def kb_start() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Bugun", callback_data="rep:today")
    kb.button(text="➕ Harajat", callback_data="exp:add")
    kb.adjust(2)
    return kb


def kb_view_expenses(date_yyyy_mm_dd: str) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(text="📋 Harajatlarni ko‘rish", callback_data=f"exp:view:{date_yyyy_mm_dd}")
    return kb


async def get_today_sales_from_dashboard(client: TwoPayClient) -> tuple[int, int, int]:
    """
    returns: total, click, cash (ints)
    """
    dash = await fetch_dashboard(client)
    summary = dash.get("summary_statistics", {})
    cash_block = summary.get("cash", {})
    click_block = summary.get("click", {})
    click_sum = _to_int(click_block.get("today_summa", 0))
    cash_sum = _to_int(cash_block.get("today_summa", 0))
    total = click_sum + cash_sum
    return total, click_sum, cash_sum


# ---- /start ----
@router.message(CommandStart())
async def start(message: Message) -> None:
    init_db()
    set_meta("report_chat_id", str(message.chat.id))  # backup sifatida qoladi

    await message.answer(
        "✅ Salom! Bot ishlayapti.\n\n"
        "Pastdagi tugmalar orqali ishlating:",
        reply_markup=kb_start().as_markup()
    )


# ---- BUGUN (callback) ----
@router.callback_query(F.data == "rep:today")
async def cb_today(callback: CallbackQuery) -> None:
    await callback.answer()
    await _send_today_report(callback.message)


# ---- /bugun (text) ----
@router.message(Command("bugun"))
async def bugun(message: Message) -> None:
    await _send_today_report(message)


async def _send_today_report(msg: Message) -> None:
    if not settings.merchant_api_token or not settings.merchant_api_base:
        await msg.answer("❌ .env da MERCHANT_API_TOKEN yoki MERCHANT_API_BASE yo'q.")
        return

    client = TwoPayClient(settings.merchant_api_base, settings.merchant_api_token, timeout=30)
    total, click_sum, cash_sum = await get_today_sales_from_dashboard(client)

    await msg.answer(
        f"sana: {format_ddmmyyyy(today_str())}\n"
        f"Umumiy to'lov: {_fmt_sum(total)} so'm\n"
        f"Clik: {_fmt_sum(click_sum)} so'm\n"
        f"Naqd: {_fmt_sum(cash_sum)} so'm",
        reply_markup=kb_start().as_markup()
    )


# ---- Harajat qo'shish (callback) ----
@router.callback_query(F.data == "exp:add")
async def cb_exp_add(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(ExpenseFlow.title)
    await callback.message.answer("Harajat nomini yozing (masalan: Benzin, Oylik, Reklama):")


@router.message(ExpenseFlow.title)
async def exp_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not title:
        await message.answer("❌ Harajat nomi bo‘sh bo‘lmasin. Qayta yozing:")
        return
    await state.update_data(title=title)
    await state.set_state(ExpenseFlow.amount)
    await message.answer("Summani yozing (faqat son). Masalan: 50000")


@router.message(ExpenseFlow.amount)
async def exp_amount(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").replace(" ", "").replace(",", "").strip()
    if not raw.isdigit():
        await message.answer("❌ Summa faqat son bo‘lsin. Masalan: 50000")
        return

    data = await state.get_data()
    title = data.get("title", "Harajat")
    amount = int(raw)

    init_db()
    date = today_str()

    # 1) Lokal DB — 100% ishlaydi
    add_expense(date, title, amount)

    # 2) ✅ Google Sheets — ishlamasa ham bot to'xtamaydi
    try:
        await asyncio.to_thread(append_expense_row, date, title, amount)
    except Exception:
        pass

    await state.clear()
    await message.answer(
        f"✅ Saqlandi: {title} — {_fmt_sum(amount)} so'm",
        reply_markup=kb_start().as_markup()
    )


# ---- Harajatlarni ko'rish ----
@router.callback_query(F.data.startswith("exp:view:"))
async def cb_exp_view(callback: CallbackQuery) -> None:
    await callback.answer()
    date = callback.data.split("exp:view:", 1)[1].strip()
    init_db()
    items = list_expenses(date)
    if not items:
        await callback.message.answer("Harajatlar yo‘q.")
        return

    lines = [f"📋 Harajatlar ({format_ddmmyyyy(date)}):"]
    total = 0
    for i, x in enumerate(items, 1):
        total += int(x["amount"])
        lines.append(f"{i}) {x['title']} — {_fmt_sum(int(x['amount']))} so'm")
    lines.append(f"\nJami: {_fmt_sum(total)} so'm")

    await callback.message.answer("\n".join(lines))


# ---- Old commands (saqlab qoldik) ----
@router.message(Command("kunlik"))
async def kunlik(message: Message) -> None:
    parts = (message.text or "").strip().split()
    if len(parts) < 2:
        await message.answer("Format: /kunlik YYYY-MM-DD")
        return
    date_yyyy_mm_dd = parts[1]

    client = TwoPayClient(settings.merchant_api_base, settings.merchant_api_token, timeout=30)

    click_items = await fetch_click_transactions(client, date_yyyy_mm_dd)
    click_sum = sum_amount(click_items)

    cash_items, _ = await fetch_cash_transactions(client, date_yyyy_mm_dd)
    cash_sum = sum_amount(cash_items or [])

    total_sum = click_sum + cash_sum

    await message.answer(
        f"sana: {format_ddmmyyyy(date_yyyy_mm_dd)}\n"
        f"Umumiy to'lov: {_fmt_sum(total_sum)} so'm\n"
        f"Clik: {_fmt_sum(click_sum)} so'm\n"
        f"Naqd: {_fmt_sum(cash_sum)} so'm"
    )


@router.message(Command("hisobot"))
async def hisobot(message: Message) -> None:
    parts = (message.text or "").strip().split()
    if len(parts) < 3:
        await message.answer("Format: /hisobot YYYY-MM-DD YYYY-MM-DD")
        return

    date_from, date_to = parts[1], parts[2]
    client = TwoPayClient(settings.merchant_api_base, settings.merchant_api_token, timeout=30)

    data = await fetch_online_transactions(
        client=client,
        page=1,
        page_size=10,
        after=date_from,
        before=date_to,
    )

    items = data.get("results", []) if isinstance(data, dict) else []
    if not items:
        await message.answer("Tranzaksiya topilmadi.")
        return

    lines = []
    for x in items[:10]:
        lines.append(f"#{x.get('id')} | {x.get('created_at')} | {x.get('amount')} so'm")

    await message.answer("\n".join(lines))