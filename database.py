"""
Async SQLite database module for bot persistence.
Handles user data, conversation history, and per-user memory storage.
"""

import json
from datetime import datetime
from typing import Any, Optional

import aiosqlite

from config import DB_PATH

# SQL for creating tables
_CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    tg_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    full_name TEXT,
    created_at TEXT NOT NULL,
    last_active TEXT NOT NULL,
    msg_count INTEGER DEFAULT 0,
    preferences TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(tg_id)
);

CREATE TABLE IF NOT EXISTS user_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(tg_id)
);

CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created ON conversations(created_at);
CREATE INDEX IF NOT EXISTS idx_user_memory_user_id ON user_memory(user_id);
CREATE INDEX IF NOT EXISTS idx_user_memory_key ON user_memory(user_id, key);
"""


async def init_db() -> None:
    """Initialize the database and create tables if they don't exist."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(_CREATE_TABLES)
        await db.commit()


async def get_or_create_user(
    tg_id: int,
    username: Optional[str] = None,
    full_name: Optional[str] = None,
) -> dict[str, Any]:
    """
    Get an existing user or create a new one.
    Updates last_active and increments msg_count on each call.
    Returns user data as a dictionary.
    """
    now = datetime.now().isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Try to get existing user
        cursor = await db.execute(
            "SELECT * FROM users WHERE tg_id = ?", (tg_id,)
        )
        row = await cursor.fetchone()

        if row:
            # Update existing user
            await db.execute(
                """UPDATE users 
                   SET last_active = ?, msg_count = msg_count + 1,
                       username = COALESCE(?, username),
                       full_name = COALESCE(?, full_name)
                   WHERE tg_id = ?""",
                (now, username, full_name, tg_id),
            )
            await db.commit()

            # Fetch updated row
            cursor = await db.execute(
                "SELECT * FROM users WHERE tg_id = ?", (tg_id,)
            )
            row = await cursor.fetchone()
        else:
            # Create new user
            await db.execute(
                """INSERT INTO users (tg_id, username, full_name, created_at, last_active, msg_count, preferences)
                   VALUES (?, ?, ?, ?, ?, 1, '{}')""",
                (tg_id, username, full_name, now, now),
            )
            await db.commit()

            cursor = await db.execute(
                "SELECT * FROM users WHERE tg_id = ?", (tg_id,)
            )
            row = await cursor.fetchone()

        return dict(row) if row else {}


async def save_message(user_id: int, role: str, content: str) -> None:
    """
    Save a message to conversation history.
    
    Args:
        user_id: Telegram user ID
        role: Message role ('user', 'assistant', 'system')
        content: Message content text
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO conversations (user_id, role, content, created_at)
               VALUES (?, ?, ?, ?)""",
            (user_id, role, content, datetime.now().isoformat()),
        )
        await db.commit()


async def get_conversation_history(
    user_id: int, limit: int = 50
) -> list[dict[str, str]]:
    """
    Get recent conversation history for a user.
    
    Args:
        user_id: Telegram user ID
        limit: Maximum number of messages to return (default: 50)
    
    Returns:
        List of dicts with 'role' and 'content' keys, ordered oldest first.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT role, content FROM conversations
               WHERE user_id = ?
               ORDER BY created_at DESC
               LIMIT ?""",
            (user_id, limit),
        )
        rows = await cursor.fetchall()

    # Reverse to get chronological order (oldest first)
    return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]


async def save_user_memory(user_id: int, key: str, value: str) -> None:
    """
    Save or update a memory entry for a user.
    If the key already exists, its value is updated.
    
    Args:
        user_id: Telegram user ID
        key: Memory key (e.g., 'name', 'favorite_color', 'city')
        value: Memory value
    """
    now = datetime.now().isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        # Check if key exists
        cursor = await db.execute(
            "SELECT id FROM user_memory WHERE user_id = ? AND key = ?",
            (user_id, key),
        )
        existing = await cursor.fetchone()

        if existing:
            await db.execute(
                """UPDATE user_memory SET value = ?, updated_at = ?
                   WHERE user_id = ? AND key = ?""",
                (value, now, user_id, key),
            )
        else:
            await db.execute(
                """INSERT INTO user_memory (user_id, key, value, updated_at)
                   VALUES (?, ?, ?, ?)""",
                (user_id, key, value, now),
            )
        await db.commit()


async def get_user_memories(user_id: int) -> dict[str, str]:
    """
    Get all stored memories for a user.
    
    Args:
        user_id: Telegram user ID
    
    Returns:
        Dictionary of key-value memory pairs.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT key, value FROM user_memory WHERE user_id = ?",
            (user_id,),
        )
        rows = await cursor.fetchall()

    return {row["key"]: row["value"] for row in rows}


async def clear_history(user_id: int) -> None:
    """
    Clear all conversation history for a user.
    Does NOT clear user memories (permanent facts about the user).
    
    Args:
        user_id: Telegram user ID
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM conversations WHERE user_id = ?", (user_id,)
        )
        await db.commit()


async def get_stats() -> dict[str, Any]:
    """
    Get overall bot statistics.
    
    Returns:
        Dictionary with total_users, total_messages, active_today counts.
    """
    today = datetime.now().date().isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        # Total users
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        total_users = (await cursor.fetchone())[0]

        # Total messages
        cursor = await db.execute("SELECT COUNT(*) FROM conversations")
        total_messages = (await cursor.fetchone())[0]

        # Active today
        cursor = await db.execute(
            "SELECT COUNT(*) FROM users WHERE last_active LIKE ?",
            (f"{today}%",),
        )
        active_today = (await cursor.fetchone())[0]

        # Total memories stored
        cursor = await db.execute("SELECT COUNT(*) FROM user_memory")
        total_memories = (await cursor.fetchone())[0]

    return {
        "total_users": total_users,
        "total_messages": total_messages,
        "active_today": active_today,
        "total_memories": total_memories,
    }
