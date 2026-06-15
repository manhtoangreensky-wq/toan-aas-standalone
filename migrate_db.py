import logging
from db import db_connect

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DB_MIGRATION")

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

        # 3. ÉP QUYỀN ADMIN CHO TÀI KHOẢN 'admin' (Sửa lỗi "Truy cập bị từ chối")
        c.execute("UPDATE users SET role = 'admin' WHERE username = 'admin'")

        # 4. Các bảng khác (PayOS, Storage)
        try:
            c.execute("ALTER TABLE payos_orders ADD COLUMN payment_type TEXT DEFAULT 'topup_xu'")
            c.execute("ALTER TABLE payos_orders ADD COLUMN package_id TEXT")
        except:
            pass
            
        c.execute('''CREATE TABLE IF NOT EXISTS storage_entitlements (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, source TEXT, payment_order_code TEXT, package_id TEXT, quota_mb INTEGER, starts_at TEXT, expires_at TEXT, status TEXT DEFAULT 'active', created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS storage_usage (user_id TEXT PRIMARY KEY, used_bytes INTEGER DEFAULT 0, updated_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS storage_events (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, event_type TEXT, delta_mb INTEGER, used_bytes_after INTEGER, ref_id TEXT, note TEXT, created_at TEXT)''')
        
        conn.commit()
        logger.info("Migrate DB thành công! Đã xử lý phân quyền Admin.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Lỗi Migrate: {e}")
    finally:
        conn.close()