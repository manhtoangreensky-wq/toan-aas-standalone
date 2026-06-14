from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging
from google import genai
import os

router = APIRouter()
logger = logging.getLogger("TOAN_AAS_VIDEO")

# Lấy Key Gemini từ biến môi trường
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

class VideoRequest(BaseModel):
    user_id: str
    topic: str
    platform: str = "tiktok" # Mặc định là tiktok

@router.post("/generate-script")
async def generate_video_script(request: VideoRequest):
    """API để Web/App gọi tạo kịch bản video bằng Gemini AI"""
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Hệ thống chưa cấu hình GEMINI_API_KEY")
        
    try:
        # Khởi tạo AI Client
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # Lập trình Prompt (Đúng chuẩn TOAN AAS Video Script Lite)
        prompt = f"""
        Bạn là chuyên gia sáng tạo nội dung viral đa nền tảng.
        Hãy tạo một kịch bản video ngắn (Dưới 1 phút) cho nền tảng {request.platform.upper()}.
        
        Chủ đề: {request.topic}
        
        Vui lòng trả về kết quả theo cấu trúc:
        1. [HOOK] - Câu mở đầu giữ chân 3s đầu.
        2. [BODY] - Nội dung chính (chia 3-4 cảnh ngắn).
        3. [CTA] - Lời kêu gọi hành động (Mua hàng/Click link).
        4. [CAPTION & HASHTAG] - Gợi ý text để đăng kèm video.
        """
        
        # Gọi Gemini
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        
        return {
            "success": True,
            "topic": request.topic,
            "platform": request.platform,
            "script": response.text
        }
        
    except Exception as e:
        logger.error(f"Lỗi gọi Gemini AI: {e}")
        raise HTTPException(status_code=500, detail="Không thể tạo kịch bản lúc này. Vui lòng thử lại.")