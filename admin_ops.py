from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging
from db import db_connect, now_text

router = APIRouter()
logger = logging.getLogger("TOAN_AAS_ADMIN")

# 1. API Lấy thống kê Tổng quan
@router.get("/dashboard-stats")
async def get_dashboard_stats(admin_id: str):
    conn = db_connect()
    c = conn.cursor()
    try:
        c.execute("SELECT role FROM users WHERE user_id=?", (admin_id,))
        admin = c.fetchone()
        if not admin or admin[0] != 'admin':
            return {"success": False, "message": "Truy cập bị từ chối"}

        # Đếm tổng user
        c.execute("SELECT COUNT(*) FROM users")
        total_users = c.fetchone()[0]

        # Tính tổng doanh thu từ PayOS
        c.execute("SELECT SUM(amount) FROM payos_orders WHERE status='PAID'")
        total_revenue = c.fetchone()[0] or 0

        return {
            "success": True, 
            "data": {
                "total_users": total_users,
                "total_revenue": total_revenue,
                "active_tools": 5 # Số lượng tool AI đang chạy
            }
        }
    except Exception as e:
        return {"success": False, "message": str(e)}
    finally:
        conn.close()

# 2. API Lấy danh sách Khách hàng
@router.get("/users")
async def get_all_users(admin_id: str):
    conn = db_connect()
    c = conn.cursor()
    try:
        c.execute("SELECT role FROM users WHERE user_id=?", (admin_id,))
        if not c.fetchone() or c.fetchone()[0] != 'admin' if c.rowcount > 0 else False: # check strict
            pass # simplified check below
        
        c.execute("SELECT role FROM users WHERE user_id=?", (admin_id,))
        admin = c.fetchone()
        if not admin or admin[0] != 'admin':
            return {"success": False, "message": "Truy cập bị từ chối"}
            
        c.execute("SELECT user_id, username, role, credits, created_at FROM users ORDER BY created_at DESC")
        users = [{"user_id": r[0], "username": r[1] or "Khách", "role": r[2], "credits": r[3], "created_at": r[4]} for r in c.fetchall()]
        return {"success": True, "data": users}
    finally:
        conn.close()

# 3. API Nạp/Trừ Xu thủ công
class AddXuReq(BaseModel):
    admin_id: str
    target_user_id: str
    amount: int

@router.post("/add-xu")
async def admin_add_xu(data: AddXuReq):
    conn = db_connect()
    c = conn.cursor()
    try:
        c.execute("BEGIN IMMEDIATE")
        c.execute("SELECT role FROM users WHERE user_id=?", (data.admin_id,))
        admin = c.fetchone()
        if not admin or admin[0] != 'admin':
            conn.rollback()
            return {"success": False, "message": "Bạn không có quyền"}
            
        c.execute("UPDATE users SET credits = credits + ? WHERE user_id=?", (data.amount, data.target_user_id))
        conn.commit()
        return {"success": True, "message": f"Đã cập nhật {data.amount} Xu thành công!"}
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": "Lỗi máy chủ"}
    finally:
        conn.close()