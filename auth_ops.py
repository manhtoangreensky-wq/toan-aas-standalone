from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import hashlib
import uuid
import logging
from db import db_connect, now_text

router = APIRouter()
logger = logging.getLogger("TOAN_AAS_AUTH")

# Tự động nâng cấp Database thêm tính năng tài khoản
def upgrade_db_for_auth():
    conn = db_connect()
    c = conn.cursor()
    try:
        c.execute("BEGIN IMMEDIATE")
        try:
            c.execute("ALTER TABLE users ADD COLUMN username TEXT")
            c.execute("ALTER TABLE users ADD COLUMN password TEXT")
            c.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
        except:
            pass # Cột đã tồn tại
        conn.commit()
    except Exception as e:
        conn.rollback()
    finally:
        conn.close()

upgrade_db_for_auth()

class AuthReq(BaseModel):
    username: str
    password: str

def hash_pwd(pwd: str):
    return hashlib.sha256(pwd.encode()).hexdigest()

@router.post("/register")
async def register(data: AuthReq):
    conn = db_connect()
    c = conn.cursor()
    try:
        c.execute("SELECT user_id FROM users WHERE username=?", (data.username,))
        if c.fetchone():
            return {"success": False, "message": "Tên đăng nhập đã có người sử dụng"}
        
        user_id = str(uuid.uuid4())
        pwd_hash = hash_pwd(data.password)
        
        # Mặc định tài khoản có tên 'admin' sẽ được cấp quyền tối cao
        role = 'admin' if data.username.lower() == 'admin' else 'user'
        
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
        c.execute("SELECT user_id, role, credits FROM users WHERE username=? AND password=?", (data.username, hash_pwd(data.password)))
        user = c.fetchone()
        if user:
            return {"success": True, "user_id": user[0], "role": user[1], "credits": user[2]}
        return {"success": False, "message": "Sai tài khoản hoặc mật khẩu!"}
    finally:
        conn.close()