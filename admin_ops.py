from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging
from db import db_connect, now_text

router = APIRouter()
logger = logging.getLogger("TOAN_AAS_ADMIN")

@router.get("/users")
async def get_all_users(admin_id: str):
    conn = db_connect()
    c = conn.cursor()
    try:
        # Kiểm tra quyền Admin
        c.execute("SELECT role FROM users WHERE user_id=?", (admin_id,))
        admin = c.fetchone()
        if not admin or admin[0] != 'admin':
            return {"success": False, "message": "Truy cập bị từ chối. Bạn không phải là Admin."}
            
        c.execute("SELECT user_id, username, role, credits, created_at FROM users ORDER BY created_at DESC")
        rows = c.fetchall()
        
        users = []
        for r in rows:
            users.append({
                "user_id": r[0],
                "username": r[1] or "Khách vãng lai (Bot)",
                "role": r[2],
                "credits": r[3],
                "created_at": r[4]
            })
        return {"success": True, "data": users}
    except Exception as e:
        logger.error(f"Lỗi lấy DS User: {e}")
        return {"success": False, "message": "Lỗi máy chủ"}
    finally:
        conn.close()

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
            return {"success": False, "message": "Bạn không có quyền thực hiện thao tác này"}
            
        c.execute("UPDATE users SET credits = credits + ? WHERE user_id=?", (data.amount, data.target_user_id))
        
        c.execute("SELECT credits FROM users WHERE user_id=?", (data.target_user_id,))
        balance_after = c.fetchone()[0]
        
        c.execute("INSERT INTO credit_events (user_id, delta, balance_after, event_type, note, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                  (data.target_user_id, data.amount, balance_after, "admin_manual", f"Admin thao tác: {data.amount} Xu", now_text()))
        
        conn.commit()
        return {"success": True, "message": f"Đã cộng {data.amount} Xu cho khách hàng!"}
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": str(e)}
    finally:
        conn.close()