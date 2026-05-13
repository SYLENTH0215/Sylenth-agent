import sqlite3
import os

DB = "sylenth.db"

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.executescript('''
        CREATE TABLE IF NOT EXISTS messages (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id    INTEGER NOT NULL,
            user_id    INTEGER NOT NULL,
            role       TEXT NOT NULL,
            content    TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS users (
            user_id    INTEGER PRIMARY KEY,
            username   TEXT,
            full_name  TEXT,
            mode       TEXT DEFAULT "chat",
            joined_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS groups (
            chat_id    INTEGER PRIMARY KEY,
            title      TEXT,
            added_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    conn.commit()
    conn.close()

def save_message(chat_id: int, user_id: int, role: str, content: str):
    conn = sqlite3.connect(DB)
    conn.execute(
        "INSERT INTO messages (chat_id, user_id, role, content) VALUES (?,?,?,?)",
        (chat_id, user_id, role, content)
    )
    conn.commit()
    conn.close()

def get_history(chat_id: int, limit: int = 12) -> list:
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT role, content FROM messages WHERE chat_id=? ORDER BY id DESC LIMIT ?",
        (chat_id, limit)
    ).fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

def clear_history(chat_id: int):
    conn = sqlite3.connect(DB)
    conn.execute("DELETE FROM messages WHERE chat_id=?", (chat_id,))
    conn.commit()
    conn.close()

def save_user(user_id: int, username: str, full_name: str):
    conn = sqlite3.connect(DB)
    conn.execute(
        "INSERT OR REPLACE INTO users (user_id, username, full_name) VALUES (?,?,?)",
        (user_id, username, full_name)
    )
    conn.commit()
    conn.close()

def save_group(chat_id: int, title: str):
    conn = sqlite3.connect(DB)
    conn.execute(
        "INSERT OR REPLACE INTO groups (chat_id, title) VALUES (?,?)",
        (chat_id, title)
    )
    conn.commit()
    conn.close()

def get_all_users() -> list:
    conn = sqlite3.connect(DB)
    rows = conn.execute("SELECT user_id FROM users").fetchall()
    conn.close()
    return [r[0] for r in rows]

def get_all_groups() -> list:
    conn = sqlite3.connect(DB)
    rows = conn.execute("SELECT chat_id FROM groups").fetchall()
    conn.close()
    return [r[0] for r in rows]
