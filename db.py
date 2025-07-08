# db.py
import sqlite3, datetime

def init_db():
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER,
            group_id INTEGER,
            username TEXT,
            xp INTEGER DEFAULT 0,
            last_daily TEXT,
            PRIMARY KEY (user_id, group_id)
        )
    """)
    conn.commit()
    conn.close()

def add_xp(user_id, group_id, username, amount):
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, group_id, username, xp) VALUES (?, ?, ?, 0)",
              (user_id, group_id, username))
    c.execute("UPDATE users SET xp = xp + ?, username = ? WHERE user_id = ? AND group_id = ?",
              (amount, username, user_id, group_id))
    conn.commit()
    conn.close()

def get_rank(user_id, group_id):
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("SELECT xp FROM users WHERE user_id = ? AND group_id = ?", (user_id, group_id))
    row = c.fetchone()
    if not row:
        return None
    xp = row[0]
    c.execute("SELECT COUNT(*) FROM users WHERE group_id = ? AND xp > ?", (group_id, xp))
    rank = c.fetchone()[0] + 1
    return xp, rank

def get_top_users(group_id, limit=10):
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("SELECT username, xp FROM users WHERE group_id = ? ORDER BY xp DESC LIMIT ?", (group_id, limit))
    top = c.fetchall()
    conn.close()
    return top

def can_claim_daily(user_id, group_id):
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("SELECT last_daily FROM users WHERE user_id = ? AND group_id = ?", (user_id, group_id))
    row = c.fetchone()
    today = datetime.date.today().isoformat()
    if row is None:
        return True
    return row[0] != today

def update_daily_claim(user_id, group_id):
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    today = datetime.date.today().isoformat()
    c.execute("UPDATE users SET last_daily = ? WHERE user_id = ? AND group_id = ?", (today, user_id, group_id))
    conn.commit()
    conn.close()
def get_total_stats(group_id):
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*), SUM(xp) FROM users WHERE group_id = ?", (group_id,))
    row = c.fetchone()
    return {"users": row[0], "xp": row[1] or 0}
