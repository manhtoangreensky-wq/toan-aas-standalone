from fastapi import APIRouter, HTTPException
import logging
from db import db_connect

router = APIRouter()
logger = logging.getLogger("TOAN_AAS_REPORT")

def table_exists(cursor, table_name: str) -> bool:
    cursor.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cursor.fetchone() is not None

def safe_count(cursor, table_name: str, where_sql: str = "", params: tuple = ()) -> int:
    if not table_exists(cursor, table_name):
        return 0
    cursor.execute(f"SELECT COUNT(*) FROM {table_name} {where_sql}", params)
    row = cursor.fetchone()
    return int(row[0] or 0)

def safe_sum(cursor, table_name: str, column_name: str, where_sql: str = "", params: tuple = ()) -> int:
    if not table_exists(cursor, table_name):
        return 0
    cursor.execute(f"SELECT SUM({column_name}) FROM {table_name} {where_sql}", params)
    row = cursor.fetchone()
    return int(row[0] or 0)

@router.get("/dashboard")
async def get_dashboard_summary():
    """API lấy số liệu tổng quan cho màn hình chính của Web/App Admin"""
    conn = db_connect()
    c = conn.cursor()
    try:
        total_users = safe_count(c, "users")

        total_revenue = safe_sum(c, "payos_orders", "amount", "WHERE status='PAID'")

        total_projects = safe_count(c, "erp_projects")

        total_campaigns = safe_count(c, "campaigns")
        total_media_assets = safe_count(c, "media_assets")
        pending_manual_orders = safe_count(c, "manual_orders", "WHERE status='pending'")

        return {
            "success": True,
            "data": {
                "total_users": total_users,
                "total_revenue_vnd": total_revenue,
                "total_b2b_projects": total_projects,
                "total_b2c_campaigns": total_campaigns,
                "total_media_assets": total_media_assets,
                "pending_manual_orders": pending_manual_orders,
            },
            "message": "Dữ liệu tổng quan hệ thống đã sẵn sàng!"
        }
    except Exception as e:
        logger.error(f"Lỗi truy xuất báo cáo: {e}")
        raise HTTPException(status_code=500, detail="Không thể tải báo cáo lúc này")
    finally:
        conn.close()
