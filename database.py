import sqlite3
from datetime import datetime

DB_PATH = "memewala.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            memes_today INTEGER DEFAULT 0,
            last_reset TEXT,
            total_memes INTEGER DEFAULT 0,
            premium BOOLEAN DEFAULT 0,
            referred_by INTEGER,
            referrals INTEGER DEFAULT 0,
            free_memes INTEGER DEFAULT 0
        )
    """)
    
    conn.commit()
    conn.close()


def get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    return {
        "user_id": row[0],
        "username": row[1],
        "first_name": row[2],
        "memes_today": row[3],
        "last_reset": row[4],
        "total_memes": row[5],
        "premium": bool(row[6]),
        "referred_by": row[7],
        "referrals": row[8],
        "free_memes": row[9],
    }


def create_user(user_id, username, first_name, referred_by=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    
    cursor.execute("""
        INSERT OR IGNORE INTO users 
        (user_id, username, first_name, last_reset, referred_by)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, username, first_name, today, referred_by))
    
    if referred_by:
        cursor.execute("""
            UPDATE users 
            SET referrals = referrals + 1, 
                free_memes = free_memes + 1
            WHERE user_id = ?
        """, (referred_by,))
    
    conn.commit()
    conn.close()


def can_create_meme(user_id):
    user = get_user(user_id)
    if not user:
        return True, "new"
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    if user["last_reset"] != today:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users 
            SET memes_today = 0, last_reset = ?
            WHERE user_id = ?
        """, (today, user_id))
        conn.commit()
        conn.close()
        user["memes_today"] = 0
    
    if user["premium"]:
        return True, "premium"
    
    if user["memes_today"] < 3:
        return True, "free"
    
    if user["free_memes"] > 0:
        return True, "bonus"
    
    return False, "limit"


def register_meme(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    user = get_user(user_id)
    
    if user and user["memes_today"] >= 3 and user["free_memes"] > 0:
        cursor.execute("""
            UPDATE users 
            SET free_memes = free_memes - 1,
                total_memes = total_memes + 1
            WHERE user_id = ?
        """, (user_id,))
    else:
        cursor.execute("""
            UPDATE users 
            SET memes_today = memes_today + 1,
                total_memes = total_memes + 1
            WHERE user_id = ?
        """, (user_id,))
    
    conn.commit()
    conn.close()


def set_premium(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users SET premium = 1 WHERE user_id = ?
    """, (user_id,))
    conn.commit()
    conn.close()