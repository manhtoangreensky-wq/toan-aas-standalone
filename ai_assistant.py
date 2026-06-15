from fastapi import APIRouter
from pydantic import BaseModel
import logging
import os
import google.generativeai as genai
from db import db_connect, now_text

router = APIRouter()
logger = logging.getLogger("TOAN_AAS_ASSISTANT")

# Đọc trực tiếp biến môi trường thay vì config
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None

class AskReq(BaseModel): user_id: str; prompt: str
PRICE_PER_ASK = 2

@router.post("/ask")
async def ask_assistant(data: AskReq):
    if not model: return {"success": False, "message": "Hệ thống chưa cấu hình AI (Thiếu GEMINI_API_KEY)."}
    conn = db_connect(); c = conn.cursor()
    try:
        c.execute("BEGIN IMMEDIATE")
        c.execute("SELECT credits FROM users WHERE user_id=?", (data.user_id,))
        user = c.fetchone()
        if not user: conn.rollback(); return {"success": False, "message": "Lỗi xác thực tài khoản!"}
            
        current_credits = user[0]
        if current_credits < PRICE_PER_ASK: conn.rollback(); return {"success": False, "message": f"Số dư không đủ! Cần {PRICE_PER_ASK} Xu."}
        
        response = model.generate_content(f"Bạn là trợ lý ảo thông minh. Trả lời: {data.prompt}")
        new_credits = current_credits - PRICE_PER_ASK
        
        c.execute("UPDATE users SET credits = ? WHERE user_id=?", (new_credits, data.user_id))
        c.execute("INSERT INTO credit_events (user_id, delta, balance_after, event_type, note, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (data.user_id, -PRICE_PER_ASK, new_credits, "ai_chat_fee", "Hỏi AI", now_text()))
        
        conn.commit()
        return {"success": True, "reply": response.text, "remaining_xu": new_credits}
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": "AI đang bận."}
    finally: conn.close()