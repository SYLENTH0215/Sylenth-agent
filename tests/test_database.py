"""
Tests for the database layer (database.py).

Feature: project-hardening
Covers Requirements 9.1, 9.2, 9.3, 13.4.

database.py imports aiosqlite at module load; the temp_db fixture skips these
tests gracefully when aiosqlite is not installed.
"""

import asyncio
import inspect

import pytest

aiosqlite = pytest.importorskip("aiosqlite")

import database


# --- Property 16: Database reads reflect writes ---------------------------
# Validates: Requirements 13.4


def test_user_round_trip(temp_db):
    async def scenario():
        user = await database.get_or_create_user(tg_id=111, username="alice", full_name="Alice A")
        assert user["tg_id"] == 111
        assert user["username"] == "alice"
        # Second call updates and increments msg_count.
        user2 = await database.get_or_create_user(tg_id=111)
        assert user2["msg_count"] == user["msg_count"] + 1

    asyncio.run(scenario())


def test_conversation_round_trip_oldest_first(temp_db):
    async def scenario():
        await database.get_or_create_user(tg_id=222, username="bob")
        await database.save_message(222, "user", "first")
        await database.save_message(222, "assistant", "second")
        await database.save_message(222, "user", "third")
        history = await database.get_conversation_history(222, limit=50)
        contents = [h["content"] for h in history]
        assert contents == ["first", "second", "third"]  # oldest first

    asyncio.run(scenario())


def test_memory_round_trip(temp_db):
    async def scenario():
        await database.get_or_create_user(tg_id=333)
        await database.save_user_memory(333, "ism", "Bob")
        await database.save_user_memory(333, "shahar", "Tashkent")
        # Update existing key.
        await database.save_user_memory(333, "ism", "Bobur")
        memories = await database.get_user_memories(333)
        assert memories == {"ism": "Bobur", "shahar": "Tashkent"}

    asyncio.run(scenario())


def test_clear_history_keeps_memory(temp_db):
    async def scenario():
        await database.get_or_create_user(tg_id=444)
        await database.save_message(444, "user", "hi")
        await database.save_user_memory(444, "ism", "Carol")
        await database.clear_history(444)
        assert await database.get_conversation_history(444) == []
        assert await database.get_user_memories(444) == {"ism": "Carol"}

    asyncio.run(scenario())


def test_property_reads_reflect_writes(temp_db):
    """Property 16 (hypothesis): arbitrary message sequences round-trip."""
    hypothesis = pytest.importorskip("hypothesis")
    from hypothesis import given, settings
    from hypothesis import strategies as st

    messages = st.lists(
        st.tuples(
            st.sampled_from(["user", "assistant"]),
            st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
        ),
        min_size=1,
        max_size=8,
    )

    @settings(max_examples=50, deadline=None)
    @given(msgs=messages)
    def run(msgs):
        async def scenario():
            tg_id = 9000
            await database.get_or_create_user(tg_id=tg_id)
            await database.clear_history(tg_id)
            for role, content in msgs:
                await database.save_message(tg_id, role, content)
            history = await database.get_conversation_history(tg_id, limit=100)
            assert [h["content"] for h in history] == [m[1] for m in msgs]

        asyncio.run(scenario())

    run()


# --- Property 8: Foreign-key enforcement rejects orphan writes ------------
# Validates: Requirements 9.2


def test_property_fk_rejects_orphan_writes(temp_db):
    """
    Property 8: a write to conversations/user_memory whose user_id does not
    reference an existing users primary key is rejected by the enforced
    connection.
    """
    import sqlite3

    async def scenario():
        async with database._connect() as db:
            with pytest.raises(sqlite3.IntegrityError):
                await db.execute(
                    "INSERT INTO conversations (user_id, role, content) VALUES (?, ?, ?)",
                    (999999, "user", "orphan"),
                )
                await db.commit()
        async with database._connect() as db:
            with pytest.raises(sqlite3.IntegrityError):
                await db.execute(
                    "INSERT INTO user_memory (user_id, key, value) VALUES (?, ?, ?)",
                    (999999, "k", "v"),
                )
                await db.commit()

    asyncio.run(scenario())


# --- Unit: FK schema shape and signature preservation ---------------------
# Validates: Requirements 9.1, 9.3


def test_fk_targets_reference_users_id(temp_db):
    async def scenario():
        async with database._connect() as db:
            for table in ("conversations", "user_memory"):
                cursor = await db.execute(f"PRAGMA foreign_key_list({table})")
                fks = await cursor.fetchall()
                assert fks, f"{table} should declare a foreign key"
                # Each FK row: (id, seq, table, from, to, on_update, on_delete, match)
                assert any(fk[2] == "users" and fk[4] == "id" for fk in fks)

    asyncio.run(scenario())


def test_public_signatures_preserved():
    """9.3: public function signatures are unchanged."""
    expected = {
        "get_or_create_user": ["tg_id", "username", "full_name"],
        "save_message": ["user_id", "role", "content"],
        "get_conversation_history": ["user_id", "limit"],
        "save_user_memory": ["user_id", "key", "value"],
        "get_user_memories": ["user_id"],
        "clear_history": ["user_id"],
        "prune_old_conversations": ["user_id", "keep_limit"],
        "get_stats": [],
        "init_db": [],
    }
    for func_name, params in expected.items():
        func = getattr(database, func_name)
        sig = inspect.signature(func)
        assert list(sig.parameters.keys()) == params, func_name
