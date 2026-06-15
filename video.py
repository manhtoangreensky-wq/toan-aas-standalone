from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import logging
import google.generativeai as genai

router = APIRouter()
logger = logging.getLogger("TOAN_AAS_VIDEO")

# Lấy Key Gemini
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

class VideoRequest(BaseModel):
    user_id: str
    topic: str
    platform: str

@router.post("/generate-script")
async def generate_script(request: VideoRequest):
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Chưa cấu hình GEMINI_API_KEY trên Railway")

    try:
        # Cấu hình AI chuẩn theo thư viện mới
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"Viết kịch bản video ngắn cho nền tảng {request.platform} với chủ đề: {request.topic}. Kịch bản cần hấp dẫn, có hook mở đầu lôi cuốn."
        
        response = model.generate_content(prompt)
        return {"success": True, "script": response.text}
    except Exception as e:
        logger.error(f"Lỗi AI Video: {e}")
        raise HTTPException(status_code=500, detail=str(e))