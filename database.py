import sqlite3

def init_db():
    conn = sqlite3.connect('sylenth_memory.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS memory 
                      (user_id INTEGER, role TEXT, content TEXT)''')
    conn.commit()
    conn.close()

def save_message(user_id, role, content):
    conn = sqlite3.connect('sylenth_memory.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO memory (user_id, role, content) VALUES (?, ?, ?)", 
                   (user_id, role, str(content)))
    conn.commit()
    conn.close()

def get_history(user_id, limit=10):
    conn = sqlite3.connect('sylenth_memory.db')
    cursor = conn.cursor()
    cursor.execute("SELECT role, content FROM memory WHERE user_id = ? ORDER BY rowid DESC LIMIT ?", 
                   (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [{"role": row[0], "content": row[1]} for row in reversed(rows)]
  
