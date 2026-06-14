import sqlite3
from datetime import datetime
from config import settings
import logging

logger = logging.getLogger("TOAN_AAS_DB")
logging.basicConfig(level=logging.INFO)

def db_connect():
    conn = sqlite3.connect(settings.DB_FILE, timeout=30)
    conn.execute("PRAGMA busy_timeout=30000")
    return conn

def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def init_db():
    conn = db_connect()
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()
    
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        username TEXT,
        credits INTEGER DEFAULT 0,
        is_vip INTEGER DEFAULT 0,
        join_date TEXT
    )""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS payos_orders (
        order_code TEXT PRIMARY KEY,
        user_id TEXT,
        amount INTEGER,
        xu INTEGER,
        status TEXT DEFAULT 'PENDING',
        created_at DATETIME,
        paid_at DATETIME
    )""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS payos_processed (
        order_code TEXT PRIMARY KEY,
        processed_at DATETIME
    )""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS credit_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        delta INTEGER,
        balance_after INTEGER,
        event_type TEXT,
        ref_id TEXT,
        note TEXT,
        created_at DATETIME
    )""")
    
    conn.commit()
    conn.close()
    logger.info("Database khởi tạo xong!")