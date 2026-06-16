import logging
from db import db_connect

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DB_MIGRATION")

def table_columns(cursor, table_name: str) -> set[str]:
    cursor.execute(f"PRAGMA table_info({table_name})")
    return {row[1] for row in cursor.fetchall()}

def add_column_if_missing(cursor, table_name: str, column_name: str, column_sql: str):
    if column_name not in table_columns(cursor, table_name):
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}")

def run_migration():
    conn = db_connect()
    c = conn.cursor()
    try:
        c.execute("BEGIN IMMEDIATE")
        
        # 1. Tạo bảng users nếu chưa có
        c.execute('''CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, credits INTEGER DEFAULT 0, created_at TEXT)''')
        
        # 2. Bơm thêm các cột còn thiếu (Dùng try-except để không bị lỗi nếu cột đã có)
        cols_to_add = [
            ("username", "TEXT"),
            ("password", "TEXT"),
            ("role", "TEXT DEFAULT 'user'")
        ]
        for col_name, col_type in cols_to_add:
            try:
                c.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
            except:
                pass

        # 3. Admin production phải xác thực server-side qua ADMIN_IDS/ADMIN_ID.
        # Không tự nâng username "admin" thành admin trong DB.

        # 4. Các bảng khác (PayOS, Storage)
        c.execute('''CREATE TABLE IF NOT EXISTS payos_orders (order_code TEXT PRIMARY KEY, user_id TEXT, amount INTEGER, xu INTEGER, status TEXT, payment_type TEXT DEFAULT 'topup_xu', package_id TEXT, created_at TEXT, paid_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS payos_processed (order_code TEXT PRIMARY KEY, payment_type TEXT, apply_status TEXT, processed_at TEXT)''')
        add_column_if_missing(c, "payos_orders", "payment_type", "payment_type TEXT DEFAULT 'topup_xu'")
        add_column_if_missing(c, "payos_orders", "package_id", "package_id TEXT")
        add_column_if_missing(c, "payos_processed", "payment_type", "payment_type TEXT")
        add_column_if_missing(c, "payos_processed", "apply_status", "apply_status TEXT")
            
        c.execute('''CREATE TABLE IF NOT EXISTS storage_entitlements (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, source TEXT, payment_order_code TEXT, package_id TEXT, quota_mb INTEGER, starts_at TEXT, expires_at TEXT, status TEXT DEFAULT 'active', created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS storage_usage (user_id TEXT PRIMARY KEY, used_bytes INTEGER DEFAULT 0, updated_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS storage_events (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, event_type TEXT, delta_mb INTEGER, used_bytes_after INTEGER, ref_id TEXT, note TEXT, created_at TEXT)''')
        
        conn.commit()
        logger.info("Migrate DB thành công. Admin auth dùng ENV server-side.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Lỗi Migrate: {e}")
    finally:
        conn.close()
