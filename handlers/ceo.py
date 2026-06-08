import asyncio
import logging
import psutil
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from config import ADMIN_ID
from database import get_stats, get_recent_users, ban_user, unban_user, get_all_user_ids, get_all_group_ids
from keyboards import ceo_panel, cancel_btn, main_menu
from states import CEOState

router = Router()

@router.callback_query(F.data == "ceo_stats")
async def ceo_stats(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("⛔", show_alert=True)
    s    = get_stats()
    cpu  = psutil.cpu_percent(interval=0.5)
    ram  = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    await callback.message.edit_text(
        f"📊 <b>SYLENTH — Statistika</b>\n\n"
        f"👥 Jami: <b>{s['total']}</b> | Bugun: <b>{s['today']}</b>\n"
        f"📈 Faol: <b>{s['active']}</b> | 🚫 Banlangan: <b>{s['banned']}</b>\n"
        f"👥 Guruhlar: <b>{s['groups']}</b> | 💬 Xabarlar: <b>{s['messages']}</b>\n\n"
        f"🖥 CPU: <b>{cpu}%</b> | RAM: <b>{ram.percent}%</b> | Disk: <b>{disk.percent}%</b>",
        parse_mode="HTML", reply_markup=ceo_panel()
    )

@router.callback_query(F.data == "ceo_users")
async def ceo_users(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("⛔", show_alert=True)
    users = get_recent_users(15)
    lines = ["👥 <b>So'nggi foydalanuvchilar:</b>\n"]
    for u in users:
        icon  = "🚫" if u["is_banned"] else "✅"
        uname = f"@{u['username']}" if u["username"] else "—"
        lines.append(f"{icon} <code>{u['sylenth_id']}</code> | <b>{u['full_name'][:20]}</b> ({uname}) | 💬{u['msg_count']}")
    await callback.message.edit_text("\n".join(lines), parse_mode="HTML", reply_markup=ceo_panel())

@router.callback_query(F.data == "ceo_broadcast")
async def ceo_broadcast_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("⛔", show_alert=True)
    await state.set_state(CEOState.broadcast)
    await callback.message.edit_text(
        "📢 Broadcast xabarini yozing:", parse_mode="HTML", reply_markup=cancel_btn()
    )

@router.message(CEOState.broadcast, F.from_user.id == ADMIN_ID)
async def ceo_broadcast_send(message: types.Message, state: FSMContext, bot: Bot):
    await state.clear()
    text    = message.text or ""
    targets = list(set(get_all_user_ids() + get_all_group_ids()))
    sent, failed = 0, 0
    status = await message.answer(f"📢 {len(targets)} ta manzilga yuborilmoqda...")
    for chat_id in targets:
        try:
            await bot.send_message(chat_id, f"📢 <b>SYLENTH:</b>\n\n{text}", parse_mode="HTML")
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.08)
    await status.delete()
    await message.answer(f"✅ Yuborildi: <b>{sent}</b> | ❌ Xato: <b>{failed}</b>",
                         parse_mode="HTML", reply_markup=ceo_panel())

@router.callback_query(F.data == "ceo_ban")
async def ceo_ban_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("⛔", show_alert=True)
    await state.set_state(CEOState.ban_input)
    await callback.message.edit_text(
        "🚫 Format: <code>tg_id sabab</code>", parse_mode="HTML", reply_markup=cancel_btn()
    )

@router.message(CEOState.ban_input, F.from_user.id == ADMIN_ID)
async def ceo_ban_execute(message: types.Message, state: FSMContext):
    await state.clear()
    parts = message.text.strip().split(maxsplit=1)
    try:
        ban_user(int(parts[0]), parts[1] if len(parts) > 1 else "Admin")
        await message.answer(f"🚫 <code>{parts[0]}</code> banlandi.", parse_mode="HTML", reply_markup=ceo_panel())
    except (ValueError, IndexError):
        await message.answer("❌ Format xato.", reply_markup=ceo_panel())

@router.callback_query(F.data == "ceo_unban")
async def ceo_unban(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("⛔", show_alert=True)
    await callback.message.edit_text("✅ Unban: <code>/unban tg_id</code>",
                                     parse_mode="HTML", reply_markup=ceo_panel())

@router.callback_query(F.data == "ceo_cleardb")
async def ceo_cleardb(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("⛔", show_alert=True)
    import sqlite3
    conn = sqlite3.connect("sylenth.db")
    conn.execute("DELETE FROM messages")
    conn.commit()
    conn.close()
    await callback.answer("🗑 Barcha xabarlar tozalandi!", show_alert=True)
    await callback.message.edit_text("🗑 Suhbat tarixi tozalandi.", reply_markup=ceo_panel())


@router.callback_query(F.data == "back_main")
async def back_main(callback: types.CallbackQuery, state: FSMContext):
    from states import UserMode
    await state.set_state(UserMode.chat)
    await callback.message.edit_text("🤖 <b>SYLENTH Agent</b>", parse_mode="HTML", reply_markup=main_menu())
