from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
import logging
from db import db_connect, now_text
from config import settings

router = APIRouter()
logger = logging.getLogger("TOAN_AAS_ASSISTANT")

# Cấu hình Gemini
try:
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    logger.error(f"Lỗi khởi tạo Gemini: {e}")

class AskReq(BaseModel):
    user_id: str
    prompt: str

PRICE_PER_ASK = 2  # Phí 2 Xu cho 1 lần hỏi

@router.post("/ask")
async def ask_assistant(data: AskReq):
    if not settings.GEMINI_API_KEY:
        return {"success": False, "message": "Hệ thống chưa cấu hình AI."}
        
    conn = db_connect()
    c = conn.cursor()
    
    try:
        c.execute("BEGIN IMMEDIATE")
        
        # 1. Kiểm tra Ví tiền
        c.execute("SELECT credits FROM users WHERE user_id=?", (data.user_id,))
        user = c.fetchone()
        
        if not user:
            conn.rollback()
            return {"success": False, "message": "Lỗi xác thực tài khoản!"}
            
        current_credits = user[0]
        if current_credits < PRICE_PER_ASK:
            conn.rollback()
            return {"success": False, "message": f"Số dư không đủ! Cần {PRICE_PER_ASK} Xu để hỏi AI. Vui lòng nạp thêm."}
        
        # 2. Gọi AI
        system_prompt = f"Bạn là trợ lý ảo thông minh của TOAN AAS OS. Hãy trả lời câu hỏi sau một cách ngắn gọn, súc tích và chuyên nghiệp: {data.prompt}"
        response = model.generate_content(system_prompt)
        ai_reply = response.text
        
        # 3. Trừ Xu
        new_credits = current_credits - PRICE_PER_ASK
        c.execute("UPDATE users SET credits = ? WHERE user_id=?", (new_credits, data.user_id))
        c.execute(
            "INSERT INTO credit_events (user_id, delta, balance_after, event_type, note, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (data.user_id, -PRICE_PER_ASK, new_credits, "ai_chat_fee", f"Hỏi AI: {data.prompt[:20]}...", now_text())
        )
        
        conn.commit()
        return {"success": True, "reply": ai_reply, "remaining_xu": new_credits}
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Lỗi AI Assistant: {e}")
        return {"success": False, "message": "AI đang bận, vui lòng thử lại sau."}
    finally:
        conn.close()