from fastapi import APIRouter, Response, HTTPException
from pydantic import BaseModel
import os
from db import db_connect
from security import is_admin_user

router = APIRouter()

# Admin password is optional legacy auth. Never ship a public default password.
ADMIN_PASS = os.environ.get("ADMIN_PASSWORD", "").strip()

class LoginData(BaseModel):
    password: str

@router.post("/verify")
async def verify_login(data: LoginData, response: Response):
    """API kiểm tra mật khẩu và cấp thẻ vào cổng (Cookie)"""
    if not ADMIN_PASS:
        raise HTTPException(status_code=503, detail="ADMIN_PASSWORD chưa được cấu hình")
    if data.password == ADMIN_PASS:
        # Cấp thẻ Cookie nhớ đăng nhập trong 30 ngày (2592000 giây)
        response.set_cookie(
            key="admin_token",
            value="logged_in",
            httponly=True,
            secure=os.environ.get("COOKIE_SECURE", "true").lower() == "true",
            samesite="strict",
            max_age=2592000,
        )
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
            role = "admin" if is_admin_user(user_id) else "user"
            return {"success": True, "username": user[0], "role": role, "credits": user[2]}
        return {"success": False, "message": "Không tìm thấy người dùng"}
    finally:
        conn.close()
