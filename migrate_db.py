import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DB_MIGRATION")

def run_migration():
    conn = sqlite3.connect("database.db") # Thay bằng tên file db của sếp nếu khác
    c = conn.cursor()
    
    try:
        c.execute("BEGIN IMMEDIATE")
        
        # 1. Thêm cột an toàn cho bảng payos_orders cũ
        try:
            c.execute("ALTER TABLE payos_orders ADD COLUMN payment_type TEXT DEFAULT 'topup_xu'")
            c.execute("ALTER TABLE payos_orders ADD COLUMN package_id TEXT")
            logger.info("Đã thêm payment_type và package_id vào payos_orders.")
        except sqlite3.OperationalError:
            logger.info("Cột payment_type đã tồn tại, bỏ qua.")

        # 2. Tạo schema Storage
        c.execute("""
            CREATE TABLE IF NOT EXISTS storage_entitlements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                source TEXT,
                payment_order_code TEXT,
                package_id TEXT,
                quota_mb INTEGER,
                starts_at TEXT,
                expires_at TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT
            )
        """)
        
        c.execute("""
            CREATE TABLE IF NOT EXISTS storage_usage (
                user_id TEXT PRIMARY KEY,
                used_bytes INTEGER DEFAULT 0,
                updated_at TEXT
            )
        """)
        
        c.execute("""
            CREATE TABLE IF NOT EXISTS storage_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                event_type TEXT,
                delta_mb INTEGER,
                used_bytes_after INTEGER,
                ref_id TEXT,
                note TEXT,
                created_at TEXT
            )
        """)
        
        conn.commit()
        logger.info("Migrate DB thành công! Hệ thống đã sẵn sàng cho Storage Add-on.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Lỗi Migrate: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()