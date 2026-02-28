# app/bot/runner.py
import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from aiogram import Bot, Dispatcher

from app.core.config import settings
from app.bot.handlers import router
from app.expenses.db import init_db, get_meta, sum_expenses
from app.merchant.client import TwoPayClient
from app.merchant.service import fetch_dashboard

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))


def _tz():
    try:
        return ZoneInfo(getattr(settings, "timezone", "Asia/Tashkent"))
    except ZoneInfoNotFoundError:
        return None


def _today_str() -> str:
    tz = _tz()
    now = datetime.now(tz) if tz else datetime.now()
    return now.strftime("%Y-%m-%d")


def _format_ddmmyyyy(date_yyyy_mm_dd: str) -> str:
    try:
        return datetime.strptime(date_yyyy_mm_dd, "%Y-%m-%d").strftime("%d.%m.%Y")
    except Exception:
        return date_yyyy_mm_dd


def _fmt(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def _to_int(v) -> int:
    try:
        return int(float(v))
    except Exception:
        return 0


async def daily_2357_job(bot: Bot) -> None:
    """
    Har kuni 23:57 da:
    Sana, Umumiy savdo (dashboard), Harajatlar (DB), Fakt qoldiq yuboradi.
    Hisobot pastida 'Harajatlarni ko‘rish' tugmasi bo‘ladi.
    """
    init_db()

    while True:
        tz = _tz()
        now = datetime.now(tz) if tz else datetime.now()

        target = now.replace(hour=23, minute=57, second=0, microsecond=0)
        if now >= target:
            target = target + timedelta(days=1)

        await asyncio.sleep((target - now).total_seconds())

        # Qayerga yuborish: avval GROUP, bo'lmasa eski chat_id (backup)
        chat_id = int(getattr(settings, "report_group_id", 0) or 0)
        if chat_id == 0:
            stored = get_meta("report_chat_id")
            if not stored:
                continue
            chat_id = int(stored)

        if not settings.merchant_api_token or not settings.merchant_api_base:
            continue

        client = TwoPayClient(settings.merchant_api_base, settings.merchant_api_token, timeout=30)

        try:
            dash = await fetch_dashboard(client)
        except Exception:
            continue

        summary = dash.get("summary_statistics", {})
        cash_block = summary.get("cash", {})
        click_block = summary.get("click", {})

        click_sum = _to_int(click_block.get("today_summa", 0))
        cash_sum = _to_int(cash_block.get("today_summa", 0))
        total_sales = click_sum + cash_sum

        date = _today_str()
        exp_sum = sum_expenses(date)
        fakt = total_sales - exp_sum

        from aiogram.utils.keyboard import InlineKeyboardBuilder
        kb = InlineKeyboardBuilder()
        kb.button(text="📋 Harajatlarni ko‘rish", callback_data=f"exp:view:{date}")

        await bot.send_message(
            chat_id,
            f"Sana: {_format_ddmmyyyy(date)}\n"
            f"Umumiy savdo: {_fmt(total_sales)} so'm\n"
            f"Harajatlar: {_fmt(exp_sum)} so'm\n"
            f"Fakt qoldiq: {_fmt(fakt)} so'm",
            reply_markup=kb.as_markup()
        )


async def main() -> None:
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()
    dp.include_router(router)

    # background job
    asyncio.create_task(daily_2357_job(bot))

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())