# app/core/config.py
from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()


class Settings(BaseModel):
    # Telegram
    bot_token: str = os.getenv("BOT_TOKEN", "")

    # Merchant API
    merchant_api_base: str = os.getenv("MERCHANT_API_BASE", "https://api.2pay.uz")
    merchant_api_token: str = os.getenv("MERCHANT_API_TOKEN", "")

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # Timezone (23:57 uchun)
    timezone: str = os.getenv("TIMEZONE", "Asia/Tashkent")

    # Daily report -> Telegram group (23:57 hisobot shu yerga boradi)
    report_group_id: int = int(os.getenv("REPORT_GROUP_ID", "0"))

    # Google Sheets (harajatlarni append qilish uchun)
    # Service Account json fayl yo'li (masalan: app/credentials/service_account.json)
    gsheet_creds_path: str = os.getenv("GSHEET_CREDS_PATH", "")
    # Google Sheet ID (linkdagi /d/<ID>/)
    gsheet_id: str = os.getenv("GSHEET_ID", "")
    # Varaq nomi (Sheet tab)
    gsheet_expenses_worksheet: str = os.getenv("GSHEET_EXPENSES_WORKSHEET", "Harajatlar")


settings = Settings()