# app/expenses/db.py
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).resolve().parents[1] / "storage" / "app.db"


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,            -- YYYY-MM-DD
        title TEXT NOT NULL,
        amount INTEGER NOT NULL,
        created_at TEXT DEFAULT (datetime('now'))
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS bot_meta (
        k TEXT PRIMARY KEY,
        v TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()


def set_meta(key: str, value: str) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO bot_meta(k,v) VALUES(?,?)", (key, value))
    conn.commit()
    conn.close()


def get_meta(key: str) -> Optional[str]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT v FROM bot_meta WHERE k=?", (key,))
    row = cur.fetchone()
    conn.close()
    return row["v"] if row else None


def add_expense(date: str, title: str, amount: int) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO expenses(date, title, amount) VALUES(?,?,?)",
        (date, title.strip(), int(amount)),
    )
    conn.commit()
    conn.close()


def list_expenses(date: str) -> list[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, title, amount, created_at FROM expenses WHERE date=? ORDER BY id ASC",
        (date,),
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def sum_expenses(date: str) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(SUM(amount),0) AS s FROM expenses WHERE date=?", (date,))
    row = cur.fetchone()
    conn.close()
    return int(row["s"] if row else 0)