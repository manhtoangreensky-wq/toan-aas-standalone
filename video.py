import os
import logging
import google.generativeai as genai
from fastapi import APIRouter
from pydantic import BaseModel
from db import db_connect, now_text

router = APIRouter()
logger = logging.getLogger("TOAN_AAS_VIDEO")

# 1. Đọc Key trực tiếp từ biến môi trường
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# 2. Cấu hình Gemini AI
try:
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
    else:
        model = None
except Exception as e:
    logger.error(f"Lỗi khởi tạo Gemini: {e}")
    model = None

class VideoRequest(BaseModel):
    user_id: str
    topic: str
    platform: str

# MỨC GIÁ: 10 XU CHO 1 LẦN TẠO KỊCH BẢN
PRICE_PER_VIDEO = 10

@router.post("/generate-script")
async def generate_script(data: VideoRequest):
    # 3. Kiểm tra API Key AI
    if not GEMINI_API_KEY or not model:
        return {"success": False, "message": "Hệ thống chưa cấu hình API Key AI."}

    conn = db_connect()
    c = conn.cursor()
    
    try:
        c.execute("BEGIN IMMEDIATE")
        
        # 1. Kiểm tra Ví tiền của khách
        c.execute("SELECT credits FROM users WHERE user_id=?", (data.user_id,))
        user = c.fetchone()
        
        if not user:
            conn.rollback()
            return {"success": False, "message": "Không tìm thấy tài khoản. Vui lòng đăng nhập lại."}
            
        current_credits = user[0]
        if current_credits < PRICE_PER_VIDEO:
            conn.rollback()
            return {"success": False, "message": f"Không đủ tiền! Tính năng này tốn {PRICE_PER_VIDEO} Xu. Trong ví bạn đang có {current_credits} Xu. Vui lòng nạp thêm!"}
        
        # 2. Gọi AI tạo kịch bản
        prompt = f"Đóng vai một chuyên gia content marketing. Hãy viết một kịch bản video chi tiết cho nền tảng {data.platform} về chủ đề: {data.topic}. Yêu cầu: Ngắn gọn, có yếu tố hook thu hút ở 3 giây đầu, phân chia rõ cảnh quay và lời thoại, có kêu gọi hành động chốt sale."
        response = model.generate_content(prompt)
        script_text = response.text
        
        # 3. Trừ tiền và Ghi biên lai
        new_credits = current_credits - PRICE_PER_VIDEO
        c.execute("UPDATE users SET credits = ? WHERE user_id=?", (new_credits, data.user_id))
        c.execute(
            "INSERT INTO credit_events (user_id, delta, balance_after, event_type, note, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (data.user_id, -PRICE_PER_VIDEO, new_credits, "ai_video_fee", f"Phí tạo kịch bản: {data.topic[:30]}", now_text())
        )
        
        conn.commit()
        return {"success": True, "script": script_text, "remaining_xu": new_credits}
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Lỗi AI: {e}")
        return {"success": False, "message": "Hệ thống AI đang bận, vui lòng thử lại sau."}
    finally:
        conn.close()