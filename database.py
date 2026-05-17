import sqlite3
import random
import logging
from datetime import datetime

DB = "sylenth.db"

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            sylenth_id  INTEGER PRIMARY KEY,
            tg_id       INTEGER UNIQUE NOT NULL,
            username    TEXT    DEFAULT "",
            full_name   TEXT    DEFAULT "",
            is_banned   INTEGER DEFAULT 0,
            warn_count  INTEGER DEFAULT 0,
            mode        TEXT    DEFAULT "chat",
            joined_at   TEXT    DEFAULT (datetime("now")),
            last_active TEXT    DEFAULT (datetime("now")),
            msg_count   INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS groups (
            chat_id   INTEGER PRIMARY KEY,
            title     TEXT DEFAULT "",
            added_at  TEXT DEFAULT (datetime("now"))
        );
        CREATE TABLE IF NOT EXISTS messages (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id    INTEGER NOT NULL,
            tg_id      INTEGER NOT NULL,
            role       TEXT NOT NULL,
            content    TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime("now"))
        );
        CREATE TABLE IF NOT EXISTS blacklist (
            tg_id      INTEGER PRIMARY KEY,
            reason     TEXT DEFAULT "",
            banned_at  TEXT DEFAULT (datetime("now"))
        );
    ''')
    conn.commit()
    conn.close()

def get_or_create_user(tg_id: int, username: str = "", full_name: str = "") -> dict:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT sylenth_id, tg_id, mode, msg_count FROM users WHERE tg_id = ?", (tg_id,))
    row = c.fetchone()
    if row:
        conn.close()
        return {"sylenth_id": row[0], "tg_id": row[1], "mode": row[2], "msg_count": row[3]}
    
    sylenth_id = random.randint(100000, 999999)
    try:
        conn.execute(
            "INSERT INTO users (sylenth_id, tg_id, username, full_name) VALUES (?, ?, ?, ?)",
            (sylenth_id, tg_id, username, full_name)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        sylenth_id = random.randint(100000, 999999)
        conn.execute(
            "INSERT INTO users (sylenth_id, tg_id, username, full_name) VALUES (?, ?, ?, ?)",
            (sylenth_id, tg_id, username, full_name)
        )
        conn.commit()
    conn.close()
    return {"sylenth_id": sylenth_id, "tg_id": tg_id, "mode": "chat", "msg_count": 0}

def get_user(tg_id: int) -> dict | None:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT sylenth_id, msg_count, is_banned FROM users WHERE tg_id = ?", (tg_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"sylenth_id": row[0], "msg_count": row[1], "is_banned": row[2]}
    return None

def is_banned(tg_id: int) -> bool:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT is_banned FROM users WHERE tg_id = ?", (tg_id,))
    row = c.fetchone()
    conn.close()
    return bool(row and row[0] == 1)

def warn_user(tg_id: int) -> int:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE users SET warn_count = warn_count + 1 WHERE tg_id = ?", (tg_id,))
    c.execute("SELECT warn_count FROM users WHERE tg_id = ?", (tg_id,))
    warns = c.fetchone()[0]
    conn.commit()
    conn.close()
    return warns

def ban_user(tg_id: int, reason: str = ""):
    conn = sqlite3.connect(DB)
    conn.execute("UPDATE users SET is_banned = 1 WHERE tg_id = ?", (tg_id,))
    conn.execute("INSERT OR REPLACE INTO blacklist (tg_id, reason) VALUES (?, ?)", (tg_id, reason))
    conn.commit()
    conn.close()

def unban_user(tg_id: int):
    conn = sqlite3.connect(DB)
    conn.execute("UPDATE users SET is_banned = 0, warn_count = 0 WHERE tg_id = ?", (tg_id,))
    conn.execute("DELETE FROM blacklist WHERE tg_id = ?", (tg_id,))
    conn.commit()
    conn.close()

def increment_msg_count(tg_id: int):
    conn = sqlite3.connect(DB)
    conn.execute("UPDATE users SET msg_count = msg_count + 1, last_active = (datetime('now')) WHERE tg_id = ?", (tg_id,))
    conn.commit()
    conn.close()

def clear_history(chat_id: int):
    conn = sqlite3.connect(DB)
    conn.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()

def save_group(chat_id: int, title: str):
    conn = sqlite3.connect(DB)
    conn.execute("INSERT OR REPLACE INTO groups (chat_id, title) VALUES (?, ?)", (chat_id, title))
    conn.commit()
    conn.close()

def save_message(chat_id: int, tg_id: int, role: str, content: str):
    conn = sqlite3.connect(DB)
    conn.execute(
        "INSERT INTO messages (chat_id, tg_id, role, content) VALUES (?, ?, ?, ?)",
        (chat_id, tg_id, role, content)
    )
    conn.commit()
    conn.close()

def get_history(chat_id: int, limit: int = 10) -> list[dict]:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        "SELECT role, content FROM messages WHERE chat_id=? ORDER BY id DESC LIMIT ?", 
        (chat_id, limit)
    )
    rows = c.fetchall()
    conn.close()
    # Tarix teskari tartibda keladi, uni to'g'rilaymiz
    return [{"role": r[0], "parts": [r[1]]} for r in reversed(rows)]

def get_stats() -> dict:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM groups")
    total_groups = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM messages")
    total_msgs = c.fetchone()[0]
    conn.close()
    return {"total": total_users, "groups": total_groups, "messages": total_msgs}

def get_all_user_ids() -> list[int]:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT tg_id FROM users WHERE is_banned = 0")
    ids = [r[0] for r in c.fetchall()]
    conn.close()
    return ids

def get_all_group_ids() -> list[int]:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT chat_id FROM groups")
    ids = [r[0] for r in c.fetchall()]
    conn.close()
    return ids

def get_recent_users(limit: int = 10) -> list[dict]:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""SELECT sylenth_id, tg_id, full_name, username, is_banned, msg_count, joined_at
                 FROM users ORDER BY joined_at DESC LIMIT ?""", (limit,))
    cols = [d[0] for d in c.description]
    rows = c.fetchall()
    conn.close()
    return [dict(zip(cols, r)) for r in rows]
    
