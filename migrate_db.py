import logging
from db import db_connect

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DB_MIGRATION")

def run_migration():
    conn = db_connect() # <--- Trỏ thẳng vào DB thật của sếp
    c = conn.cursor()
    
    try:
        c.execute("BEGIN IMMEDIATE")
        
        try:
            c.execute("ALTER TABLE payos_orders ADD COLUMN payment_type TEXT DEFAULT 'topup_xu'")
            c.execute("ALTER TABLE payos_orders ADD COLUMN package_id TEXT")
            logger.info("Đã thêm payment_type vào payos_orders.")
        except:
            pass # Bỏ qua nếu cột đã tồn tại

        # Tạo bảng Storage
        c.execute("""CREATE TABLE IF NOT EXISTS storage_entitlements (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, source TEXT, payment_order_code TEXT, package_id TEXT, quota_mb INTEGER, starts_at TEXT, expires_at TEXT, status TEXT DEFAULT 'active', created_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS storage_usage (user_id TEXT PRIMARY KEY, used_bytes INTEGER DEFAULT 0, updated_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS storage_events (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, event_type TEXT, delta_mb INTEGER, used_bytes_after INTEGER, ref_id TEXT, note TEXT, created_at TEXT)""")
        
        conn.commit()
        logger.info("Migrate DB thành công!")
    except Exception as e:
        conn.rollback()
        logger.error(f"Lỗi Migrate: {e}")
    finally:
        conn.close()