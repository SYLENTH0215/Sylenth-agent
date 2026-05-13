def clear_history(user_id):
    import sqlite3
    conn = sqlite3.connect('chat_history.db') # Bazang nomi qanday bo'lsa shuni yoz
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    print(f"Foydalanuvchi {user_id} uchun xotira tozalandi!")
    
