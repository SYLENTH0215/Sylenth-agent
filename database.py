import sqlite3
import random
import logging
from datetime import datetime

DB = "sylenth.db"

def init_db():
    """Database-ni yaratish va tabelalarni o'rnatish"""
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
    logging.info("✅ Database ishga tushdi!")

def get_or_create_user(tg_id: int, username: str = "", full_name: str = "") -> dict:
    """Foydalanuvchini olish yoki yaratish"""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT sylenth_id, tg_id, mode, msg_count FROM users WHERE tg_id = ?", (tg_id,))
    row = c.fetchone()
    
    if row:
        conn.close()
        return {"sylenth_id": row[0], "tg_id": row[1], "mode": row[2], "msg_count": row[3]}
    
    # Yangi foydalanuvchi yaratish
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
    """Foydalanuvchi ma'lumotlarini olish"""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT sylenth_id, msg_count, is_banned, joined_at FROM users WHERE tg_id = ?", (tg_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"sylenth_id": row[0], "msg_count": row[1], "is_banned": row[2], "joined_at": row[3]}
    return None

def is_banned(tg_id: int) -> bool:
    """Foydalanuvchi ban qilinganligini tekshirish"""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT is_banned FROM users WHERE tg_id = ?", (tg_id,))
    row = c.fetchone()
    conn.close()
    return bool(row and row[0] == 1)

def warn_user(tg_id: int) -> int:
    """Foydalanuvchiga ogohlantirish"""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE users SET warn_count = warn_count + 1 WHERE tg_id = ?", (tg_id,))
    c.execute("SELECT warn_count FROM users WHERE tg_id = ?", (tg_id,))
    warns = c.fetchone()[0]
    conn.commit()
    conn.close()
    return warns

def ban_user(tg_id: int, reason: str = ""):
    """Foydalanuvchini ban qilish"""
    conn = sqlite3.connect(DB)
    conn.execute("UPDATE users SET is_banned = 1 WHERE tg_id = ?", (tg_id,))
    conn.execute("INSERT OR REPLACE INTO blacklist (tg_id, reason) VALUES (?, ?)", (tg_id, reason))
    conn.commit()
    conn.close()

def unban_user(tg_id: int):
    """Foydalanuvchini ban dan chiqarish"""
    conn = sqlite3.connect(DB)
    conn.execute("UPDATE users SET is_banned = 0, warn_count = 0 WHERE tg_id = ?", (tg_id,))
    conn.execute("DELETE FROM blacklist WHERE tg_id = ?", (tg_id,))
    conn.commit()
    conn.close()

def increment_msg_count(tg_id: int):
    """Xabar sonini oshirish"""
    conn = sqlite3.connect(DB)
    conn.execute("UPDATE users SET msg_count = msg_count + 1, last_active = (datetime('now')) WHERE tg_id = ?", (tg_id,))
    conn.commit()
    conn.close()

def clear_history(chat_id: int):
    """Suhbat tarixini tozalash"""
    conn = sqlite3.connect(DB)
    conn.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()

def save_group(chat_id: int, title: str):
    """Guruhni saqlash"""
    conn = sqlite3.connect(DB)
    conn.execute("INSERT OR REPLACE INTO groups (chat_id, title) VALUES (?, ?)", (chat_id, title))
    conn.commit()
    conn.close()

def save_message(chat_id: int, tg_id: int, role: str, content: str):
    """Xabarni saqlash"""
    conn = sqlite3.connect(DB)
    conn.execute(
        "INSERT INTO messages (chat_id, tg_id, role, content) VALUES (?, ?, ?, ?)",
        (chat_id, tg_id, role, content)
    )
    conn.commit()
    conn.close()

def get_history(chat_id: int, limit: int = 10) -> list[dict]:
    """Suhbat tarixini olish"""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        "SELECT role, content FROM messages WHERE chat_id=? ORDER BY id DESC LIMIT ?", 
        (chat_id, limit)
    )
    rows = c.fetchall()
    conn.close()
    return [{"role": r[0], "parts": [r[1]]} for r in reversed(rows)]

def get_stats() -> dict:
    """Statistikani olish"""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    # Jami foydalanuvchilar
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    # Bugun qo'shilganlar
    c.execute("SELECT COUNT(*) FROM users WHERE joined_at > datetime('now', '-1 day')")
    today_users = c.fetchone()[0]
    
    # Faol foydalanuvchilar (24 soat ichida)
    c.execute("SELECT COUNT(*) FROM users WHERE last_active > datetime('now', '-1 day')")
    active = c.fetchone()[0]
    
    # Banlangan foydalanuvchilar
    c.execute("SELECT COUNT(*) FROM users WHERE is_banned = 1")
    banned = c.fetchone()[0]
    
    # Guruhlar
    c.execute("SELECT COUNT(*) FROM groups")
    total_groups = c.fetchone()[0]
    
    # Xabarlar
    c.execute("SELECT COUNT(*) FROM messages")
    total_msgs = c.fetchone()[0]
    
    conn.close()
    
    return {
        "total": total_users,
        "today": today_users,
        "active": active,
        "banned": banned,
        "groups": total_groups,
        "messages": total_msgs
    }

def get_all_user_ids() -> list[int]:
    """Barcha ban qilinmagan foydalanuvchilarning IDlarini olish"""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT tg_id FROM users WHERE is_banned = 0")
    ids = [r[0] for r in c.fetchall()]
    conn.close()
    return ids

def get_all_group_ids() -> list[int]:
    """Barcha guruhlarning IDlarini olish"""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT chat_id FROM groups")
    ids = [r[0] for r in c.fetchall()]
    conn.close()
    return ids

def get_recent_users(limit: int = 10) -> list[dict]:
    """So'nggi qo'shilgan foydalanuvchilarni olish"""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""SELECT sylenth_id, tg_id, full_name, username, is_banned, msg_count, joined_at
                 FROM users ORDER BY joined_at DESC LIMIT ?""", (limit,))
    cols = [d[0] for d in c.description]
    rows = c.fetchall()
    conn.close()
    return [dict(zip(cols, r)) for r in rows]
