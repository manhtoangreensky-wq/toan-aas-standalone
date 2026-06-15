from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import logging
import google.generativeai as genai

router = APIRouter()
logger = logging.getLogger("TOAN_AAS_COACH")

# Tự động lấy Key Gemini đã có sẵn của sếp
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

class CoachRequest(BaseModel):
    product_name: str
    views: int
    clicks: int
    revenue: int

@router.post("/analyze")
async def analyze_campaign(request: CoachRequest):
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Chưa cấu hình GEMINI_API_KEY")

    genai.configure(api_key=GEMINI_API_KEY)
    
    # AI tự tính toán xác suất tỷ lệ chuyển đổi
    ctr = (request.clicks / request.views * 100) if request.views > 0 else 0
    
    prompt = f"""Bạn là một chuyên gia Growth Marketing thực chiến. 
    Tôi đang chạy chiến dịch bán sản phẩm: '{request.product_name}'.
    Số liệu thống kê hiện tại:
    - Lượt xem (Views): {request.views}
    - Lượt bấm link (Clicks): {request.clicks} (Tỷ lệ CTR: {ctr:.2f}%)
    - Doanh thu: {request.revenue} VNĐ

    Hãy phân tích ngắn gọn, súc tích (dưới 150 chữ) theo 2 phần rõ ràng:
    1. CHẨN ĐOÁN (Ví dụ: CTR thấp do content yếu, hay Click cao không đơn do sai tệp khách hàng).
    2. HÀNH ĐỘNG (Lời khuyên cần sửa kịch bản thế nào, đổi hook ra sao).
    """

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return {"success": True, "advice": response.text}
    except Exception as e:
        logger.error(f"Lỗi AI Coach: {e}")
        raise HTTPException(status_code=500, detail="Lỗi kết nối bộ não AI")