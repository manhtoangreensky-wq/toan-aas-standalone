from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import hashlib
import uuid
import logging
from db import db_connect, now_text
from security import is_admin_user

router = APIRouter()
logger = logging.getLogger("TOAN_AAS_AUTH")

# Tự động nâng cấp Database thêm tính năng tài khoản
def upgrade_db_for_auth():
    conn = db_connect()
    c = conn.cursor()
    try:
        c.execute("BEGIN IMMEDIATE")
        c.execute("PRAGMA table_info(users)")
        existing = {row[1] for row in c.fetchall()}
        for column_name, column_sql in [
            ("username", "username TEXT"),
            ("password", "password TEXT"),
            ("role", "role TEXT DEFAULT 'user'"),
        ]:
            if column_name not in existing:
                c.execute(f"ALTER TABLE users ADD COLUMN {column_sql}")
        conn.commit()
    except Exception as e:
        conn.rollback()
    finally:
        conn.close()

upgrade_db_for_auth()

class AuthReq(BaseModel):
    username: str = ""
    password: str = ""
    user_id: str = ""

def hash_pwd(pwd: str):
    return hashlib.sha256(pwd.encode()).hexdigest()

@router.post("/register")
async def register(data: AuthReq):
    conn = db_connect()
    c = conn.cursor()
    try:
        if not data.username.strip() or not data.password:
            return {"success": False, "message": "Vui lòng nhập tên đăng nhập và mật khẩu"}
        c.execute("SELECT user_id FROM users WHERE username=?", (data.username,))
        if c.fetchone():
            return {"success": False, "message": "Tên đăng nhập đã có người sử dụng"}
        
        user_id = str(uuid.uuid4())
        pwd_hash = hash_pwd(data.password)
        
        role = 'user'
        
        c.execute("INSERT INTO users (user_id, username, password, role, credits, created_at) VALUES (?, ?, ?, ?, 0, ?)",
                  (user_id, data.username, pwd_hash, role, now_text()))
        conn.commit()
        return {"success": True, "user_id": user_id, "role": role}
    except Exception as e:
        return {"success": False, "message": str(e)}
    finally:
        conn.close()

@router.post("/login")
async def login(data: AuthReq):
    conn = db_connect()
    c = conn.cursor()
    try:
        if data.user_id:
            c.execute("SELECT user_id, username, credits FROM users WHERE user_id=?", (data.user_id,))
            user = c.fetchone()
            if user:
                role = "admin" if is_admin_user(user[0]) else "user"
                return {
                    "success": True,
                    "user_id": user[0],
                    "username": user[1] or "Member",
                    "role": role,
                    "credits": user[2],
                }
            return {"success": False, "message": "Tài khoản chưa tồn tại! Hãy vào Bot Telegram gõ /start trước."}

        if not data.username.strip() or not data.password:
            return {"success": False, "message": "Vui lòng nhập tài khoản và mật khẩu"}

        c.execute("SELECT user_id, role, credits FROM users WHERE username=? AND password=?", (data.username, hash_pwd(data.password)))
        user = c.fetchone()
        if user:
            role = "admin" if is_admin_user(user[0]) else "user"
            return {"success": True, "user_id": user[0], "role": role, "credits": user[2]}
        return {"success": False, "message": "Sai tài khoản hoặc mật khẩu!"}
    finally:
        conn.close()

@router.get("/me/{user_id}")
async def me(user_id: str):
    conn = db_connect()
    c = conn.cursor()
    try:
        c.execute("SELECT user_id, username, credits FROM users WHERE user_id=?", (str(user_id),))
        user = c.fetchone()
        if not user:
            return {"success": False, "message": "Tài khoản chưa tồn tại"}
        role = "admin" if is_admin_user(user[0]) else "user"
        return {
            "success": True,
            "user_id": user[0],
            "username": user[1] or "Member",
            "role": role,
            "credits": int(user[2] or 0),
        }
    finally:
        conn.close()
