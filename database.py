import sqlite3
import random
import logging

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
        CREATE INDEX IF NOT EXISTS idx_messages_chat ON messages(chat_id);
        CREATE INDEX IF NOT EXISTS idx_users_tg ON users(tg_id);
    ''')
    conn.commit()
    conn.close()

def _generate_unique_sylenth_id(cursor) -> int:
    for _ in range(100):
        uid = random.randint(100000, 999999)
        cursor.execute("SELECT 1 FROM users WHERE sylenth_id=?", (uid,))
        if not cursor.fetchone():
            return uid
    raise RuntimeError("Noyob ID yaratib bo'lmadi")

def get_or_create_user(tg_id, username="", full_name=""):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE tg_id=?", (tg_id,))
    row = c.fetchone()
    if row:
        c.execute("UPDATE users SET last_active=datetime('now'), username=?, full_name=? WHERE tg_id=?",
                  (username, full_name, tg_id))
        conn.commit()
        cols = [d[0] for d in c.description]
        user = dict(zip(cols, row))
    else:
        sid = _generate_unique_sylenth_id(c)
        c.execute("INSERT INTO users (sylenth_id,tg_id,username,full_name) VALUES (?,?,?,?)",
                  (sid, tg_id, username, full_name))
        conn.commit()
        c.execute("SELECT * FROM users WHERE tg_id=?", (tg_id,))
        row2 = c.fetchone()
        cols = [d[0] for d in c.description]
        user = dict(zip(cols, row2))
    conn.close()
    return user

def get_user(tg_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE tg_id=?", (tg_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return None
    cols = [d[0] for d in c.description]
    conn.close()
    return dict(zip(cols, row))

def increment_msg_count(tg_id):
    conn = sqlite3.connect(DB)
    conn.execute("UPDATE users SET msg_count=msg_count+1, last_active=datetime('now') WHERE tg_id=?", (tg_id,))
    conn.commit()
    conn.close()

def set_user_mode(tg_id, mode):
    conn = sqlite3.connect(DB)
    conn.execute("UPDATE users SET mode=? WHERE tg_id=?", (mode, tg_id))
    conn.commit()
    conn.close()

def ban_user(tg_id, reason="Admin buyrug'i"):
    conn = sqlite3.connect(DB)
    conn.execute("UPDATE users SET is_banned=1 WHERE tg_id=?", (tg_id,))
    conn.execute("INSERT OR REPLACE INTO blacklist (tg_id, reason) VALUES (?,?)", (tg_id, reason))
    conn.commit()
    conn.close()

def unban_user(tg_id):
    conn = sqlite3.connect(DB)
    conn.execute("UPDATE users SET is_banned=0, warn_count=0 WHERE tg_id=?", (tg_id,))
    conn.execute("DELETE FROM blacklist WHERE tg_id=?", (tg_id,))
    conn.commit()
    conn.close()

def warn_user(tg_id):
    conn = sqlite3.connect(DB)
    conn.execute("UPDATE users SET warn_count=warn_count+1 WHERE tg_id=?", (tg_id,))
    conn.commit()
    c = conn.cursor()
    c.execute("SELECT warn_count FROM users WHERE tg_id=?", (tg_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def is_banned(tg_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT is_banned FROM users WHERE tg_id=?", (tg_id,))
    row = c.fetchone()
    conn.close()
    return bool(row and row[0])

def get_all_user_ids():
    conn = sqlite3.connect(DB)
    rows = conn.execute("SELECT tg_id FROM users WHERE is_banned=0").fetchall()
    conn.close()
    return [r[0] for r in rows]

def get_all_group_ids():
    conn = sqlite3.connect(DB)
    rows = conn.execute("SELECT chat_id FROM groups").fetchall()
    conn.close()
    return [r[0] for r in rows]

def get_stats():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    total  = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    banned = c.execute("SELECT COUNT(*) FROM users WHERE is_banned=1").fetchone()[0]
    groups = c.execute("SELECT COUNT(*) FROM groups").fetchone()[0]
    today  = c.execute("SELECT COUNT(*) FROM users WHERE date(joined_at)=date('now')").fetchone()[0]
    active = c.execute("SELECT COUNT(*) FROM users WHERE date(last_active)=date('now')").fetchone()[0]
    msgs   = c.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    conn.close()
    return {"total": total, "banned": banned, "groups": groups,
            "today": today, "active": active, "messages": msgs}

def get_recent_users(limit=10):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT sylenth_id,tg_id,full_name,username,is_banned,msg_count,joined_at FROM users ORDER BY joined_at DESC LIMIT ?", (limit,))
    cols = [d[0] for d in c.description]
    rows = c.fetchall()
    conn.close()
    return [dict(zip(cols, r)) for r in rows]

def save_group(chat_id, title):
    conn = sqlite3.connect(DB)
    conn.execute("INSERT OR REPLACE INTO groups (chat_id, title) VALUES (?,?)", (chat_id, title))
    conn.commit()
    conn.close()

def save_message(chat_id, tg_id, role, content):
    conn = sqlite3.connect(DB)
    conn.execute("INSERT INTO messages (chat_id,tg_id,role,content) VALUES (?,?,?,?)",
                 (chat_id, tg_id, role, content))
    conn.commit()
    conn.close()

def get_history(chat_id, limit=10):
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT role, content FROM messages WHERE chat_id=? ORDER BY id DESC LIMIT ?",
        (chat_id, limit)
    ).fetchall()
    conn.close()
    return [{"role": r[0], "parts": [r[1]]} for r in reversed(rows)]

def clear_history(chat_id):
    conn = sqlite3.connect(DB)
    conn.execute("DELETE FROM messages WHERE chat_id=?", (chat_id,))
    conn.commit()
    conn.close()
