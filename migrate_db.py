import logging
from db import db_connect

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DB_MIGRATION")

def run_migration():
    conn = db_connect()
    c = conn.cursor()
    try:
        c.execute("BEGIN IMMEDIATE")
        
        # 1. Vá lỗi bảng thanh toán
        try:
            c.execute("ALTER TABLE payos_orders ADD COLUMN payment_type TEXT DEFAULT 'topup_xu'")
            c.execute("ALTER TABLE payos_orders ADD COLUMN package_id TEXT")
        except:
            pass

        # 2. VÁ LỖI BẢNG TÀI KHOẢN (FIX LỖI ĐĂNG KÝ)
        c.execute('''CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, credits INTEGER DEFAULT 0, created_at TEXT)''')
        try:
            c.execute("ALTER TABLE users ADD COLUMN username TEXT")
            c.execute("ALTER TABLE users ADD COLUMN password TEXT")
            c.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
        except:
            pass # Bỏ qua nếu cột đã được tạo

        # 3. Tạo các bảng lưu trữ Storage
        c.execute('''CREATE TABLE IF NOT EXISTS storage_entitlements (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, source TEXT, payment_order_code TEXT, package_id TEXT, quota_mb INTEGER, starts_at TEXT, expires_at TEXT, status TEXT DEFAULT 'active', created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS storage_usage (user_id TEXT PRIMARY KEY, used_bytes INTEGER DEFAULT 0, updated_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS storage_events (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, event_type TEXT, delta_mb INTEGER, used_bytes_after INTEGER, ref_id TEXT, note TEXT, created_at TEXT)''')
        
        conn.commit()
        logger.info("Migrate DB thành công! Đã vá lỗi bảng users.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Lỗi Migrate: {e}")
    finally:
        conn.close()