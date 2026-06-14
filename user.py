from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging
from db import db_connect, now_text

router = APIRouter()
logger = logging.getLogger("TOAN_AAS_USER")

# --- Kịch bản dữ liệu trả về cho App ---
class UserResponse(BaseModel):
    user_id: str
    username: str | None
    credits: int
    is_vip: int
    join_date: str | None

class UserCreate(BaseModel):
    user_id: str
    username: str = ""

# --- API 1: Lấy thông tin Profile ---
@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    """App gọi API này để lấy số dư Xu và trạng thái VIP của khách hiển thị lên màn hình"""
    conn = db_connect()
    c = conn.cursor()
    try:
        c.execute("SELECT user_id, username, credits, is_vip, join_date FROM users WHERE user_id=?", (user_id,))
        row = c.fetchone()
        if row:
            return UserResponse(
                user_id=row[0],
                username=row[1],
                credits=row[2],
                is_vip=row[3],
                join_date=row[4]
            )
        else:
            raise HTTPException(status_code=404, detail="Không tìm thấy user")
    finally:
        conn.close()

# --- API 2: Đồng bộ User mới vào hệ thống ---
@router.post("/sync")
async def sync_user(user_data: UserCreate):
    """Khi khách đăng nhập lần đầu vào App, gọi API này để tạo tài khoản & tặng 200 Xu dùng thử"""
    conn = db_connect()
    c = conn.cursor()
    try:
        # Kiểm tra xem khách đã tồn tại chưa
        c.execute("SELECT 1 FROM users WHERE user_id=?", (user_data.user_id,))
        exists = c.fetchone()
        
        if not exists:
            # Nếu khách mới -> Lưu database và tặng 200 Xu trải nghiệm
            c.execute(
                "INSERT INTO users (user_id, username, credits, is_vip, join_date) VALUES (?, ?, ?, ?, ?)",
                (user_data.user_id, user_data.username, 200, 0, now_text())
            )
            conn.commit()
            return {"success": True, "message": "Đã tạo user và tặng 200 Xu trải nghiệm", "is_new": True}
        else:
            # Nếu khách cũ -> Cập nhật lại username cho mới nhất
            c.execute("UPDATE users SET username=? WHERE user_id=?", (user_data.username, user_data.user_id))
            conn.commit()
            return {"success": True, "message": "Đã đồng bộ user cũ", "is_new": False}
    except Exception as e:
        conn.rollback()
        logger.error(f"Lỗi DB Sync User: {e}")
        raise HTTPException(status_code=500, detail="Lỗi xử lý Database")
    finally:
        conn.close()