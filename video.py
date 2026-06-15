import os
import logging
import google.generativeai as genai
from fastapi import APIRouter
from pydantic import BaseModel

# Kéo vũ khí hạng nặng từ bot.py sang (Tự động free cho Admin, tự tạo TK nếu thiếu)
from bot import spend_fixed_credit, get_user

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
    # 1. Kiểm tra API Key AI
    if not GEMINI_API_KEY or not model:
        return {"success": False, "message": "Hệ thống chưa cấu hình API Key AI."}

    # 2. Xử lý Trừ Xu thông minh (Miễn phí hoàn toàn cho Admin, tự tạo TK nếu chưa có)
    # Hàm spend_fixed_credit sẽ trả về True luôn nếu user_id == ADMIN_ID
    success = spend_fixed_credit(
        user_id=data.user_id, 
        amount=PRICE_PER_VIDEO, 
        event_type="ai_video_fee", 
        note=f"Phí tạo kịch bản: {data.topic[:30]}"
    )
    
    if not success:
        return {"success": False, "message": f"Không đủ tiền! Tính năng này tốn {PRICE_PER_VIDEO} Xu. Vui lòng nạp thêm!"}
    
    try:
        # 3. Gọi AI tạo kịch bản
        prompt = f"Đóng vai một chuyên gia content marketing. Hãy viết một kịch bản video chi tiết cho nền tảng {data.platform} về chủ đề: {data.topic}. Yêu cầu: Ngắn gọn, có yếu tố hook thu hút ở 3 giây đầu, phân chia rõ cảnh quay và lời thoại, có kêu gọi hành động chốt sale."
        response = model.generate_content(prompt)
        script_text = response.text
        
        # 4. Lấy lại số dư mới nhất để hiển thị cho Web
        credits, _, _ = get_user(data.user_id)
        
        return {"success": True, "script": script_text, "remaining_xu": credits}
        
    except Exception as e:
        logger.error(f"Lỗi AI: {e}")
        return {"success": False, "message": "Hệ thống AI đang bận, vui lòng thử lại sau."}