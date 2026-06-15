from fastapi import APIRouter, Response, HTTPException
from pydantic import BaseModel
import os

router = APIRouter()

# Lấy mật khẩu từ Railway, nếu chưa cài thì mặc định là toanaas2026
ADMIN_PASS = os.environ.get("ADMIN_PASSWORD", "toanaas2026")

class LoginData(BaseModel):
    password: str

@router.post("/verify")
async def verify_login(data: LoginData, response: Response):
    """API kiểm tra mật khẩu và cấp thẻ vào cổng (Cookie)"""
    if data.password == ADMIN_PASS:
        # Cấp thẻ Cookie nhớ đăng nhập trong 30 ngày (2592000 giây)
        response.set_cookie(key="admin_token", value="logged_in", httponly=True, max_age=2592000)
        return {"success": True, "message": "Đăng nhập thành công!"}
    else:
        raise HTTPException(status_code=401, detail="Sai mật khẩu!")

@router.post("/logout")
async def logout(response: Response):
    """API Đăng xuất, hủy thẻ Cookie"""
    response.delete_cookie("admin_token")
    return {"success": True}

@router.get("/me/{user_id}")
async def get_my_profile(user_id: str):
    conn = db_connect()
    c = conn.cursor()
    try:
        c.execute("SELECT username, role, credits FROM users WHERE user_id=?", (user_id,))
        user = c.fetchone()
        if user:
            return {"success": True, "username": user[0], "role": user[1], "credits": user[2]}
        return {"success": False, "message": "Không tìm thấy người dùng"}
    finally:
        conn.close()