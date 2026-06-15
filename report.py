from fastapi import APIRouter, HTTPException
import logging
from db import db_connect

router = APIRouter()
logger = logging.getLogger("TOAN_AAS_REPORT")

@router.get("/dashboard")
async def get_dashboard_summary():
    """API lấy số liệu tổng quan cho màn hình chính của Web/App Admin"""
    conn = db_connect()
    c = conn.cursor()
    try:
        # 1. Đếm tổng khách hàng
        c.execute("SELECT COUNT(*) FROM users")
        total_users = c.fetchone()[0]

        # 2. Tính tổng doanh thu tiền mặt (PayOS đã thanh toán)
        c.execute("SELECT SUM(amount) FROM payos_orders WHERE status='PAID'")
        total_revenue = c.fetchone()[0] or 0

        # 3. Tính tổng dự án kỹ thuật (B2B)
        total_projects = 0
        c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='projects'")
        if c.fetchone():
            c.execute("SELECT COUNT(*) FROM projects")
            total_projects = c.fetchone()[0]

        # 4. Đếm số chiến dịch Affiliate (B2C)
        total_campaigns = 0
        c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='campaigns'")
        if c.fetchone():
            c.execute("SELECT COUNT(*) FROM campaigns")
            total_campaigns = c.fetchone()[0]

        return {
            "success": True,
            "data": {
                "total_users": total_users,
                "total_revenue_vnd": total_revenue,
                "total_b2b_projects": total_projects,
                "total_b2c_campaigns": total_campaigns
            },
            "message": "Dữ liệu tổng quan hệ thống đã sẵn sàng!"
        }
    except Exception as e:
        logger.error(f"Lỗi truy xuất báo cáo: {e}")
        raise HTTPException(status_code=500, detail="Không thể tải báo cáo lúc này")
    finally:
        conn.close()