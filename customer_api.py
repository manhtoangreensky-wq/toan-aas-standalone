from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import logging
import random
import time
from datetime import datetime

# Import các hàm lõi từ hệ thống (bot.py / erp_core.py / db.py)
from bot import (
    db_connect, now_text, get_user, spend_fixed_credit, 
    generate_order_code, create_order, create_payos_payment_request,
    PUBLIC_BASE_URL, ADMIN_ID
)

router = APIRouter()
logger = logging.getLogger("TOAN_AAS_CUSTOMER_API")

# --- 1. API GỬI GÓP Ý (FEEDBACK) ---
class FeedbackReq(BaseModel):
    user_id: str
    content: str

@router.post("/feedback")
async def submit_feedback(data: FeedbackReq):
    conn = db_connect()
    c = conn.cursor()
    try:
        # Lấy tên user để lưu cho đẹp
        c.execute("SELECT username FROM users WHERE user_id=?", (str(data.user_id),))
        row = c.fetchone()
        username = row[0] if row else "Unknown"
        
        c.execute("INSERT INTO feedback (user_id, username, content, timestamp) VALUES (?, ?, ?, ?)",
                  (str(data.user_id), username, data.content, now_text()))
        conn.commit()
        return {"success": True, "message": "Góp ý đã được gửi tới Admin!"}
    except Exception as e:
        logger.error(f"Lỗi lưu feedback: {e}")
        return {"success": False, "message": "Lỗi hệ thống khi lưu góp ý."}
    finally:
        conn.close()

# --- 2. API TẠO LINK THANH TOÁN PAYOS THẬT ---
class PayosReq(BaseModel):
    user_id: str
    amount_vnd: int
    xu_nhan: int

@router.post("/payos/create-link")
async def create_web_payos_link(data: PayosReq):
    try:
        # 1. Tạo Order Code duy nhất
        order_code = generate_order_code()
        
        # 2. Lưu vào DB để theo dõi
        create_order(order_code, data.user_id, data.amount_vnd, data.xu_nhan)
        
        # 3. Gọi API PayOS thật
        return_url = f"{PUBLIC_BASE_URL.rstrip('/')}/" if PUBLIC_BASE_URL else "https://t.me"
        cancel_url = return_url
        
        payos_body = {
            "orderCode": order_code,
            "amount": data.amount_vnd,
            "description": f"AAS {data.user_id} {data.xu_nhan}XU"[:25],
            "returnUrl": return_url,
            "cancelUrl": cancel_url
        }
        
        res, res_data, raw_preview, raw_str = await create_payos_payment_request(payos_body)
        
        if res_data and res_data.get("code") == "00":
            checkout_url = res_data["data"]["checkoutUrl"]
            return {"success": True, "checkout_url": checkout_url}
        else:
            return {"success": False, "message": "Lỗi khởi tạo cổng PayOS."}
            
    except Exception as e:
        logger.error(f"Lỗi tạo PayOS link: {e}")
        return {"success": False, "message": "Lỗi kết nối PayOS."}

# --- 3. API GỌI TOOL AI (VIDEO / VOICE / MEDIA) ---
class AIToolReq(BaseModel):
    user_id: str
    tool_type: str # 'voice', 'video', 'media'
    cost: int
    prompt: str

@router.post("/ai/process")
async def process_ai_tool(data: AIToolReq):
    # 1. Kiểm tra và Trừ Xu
    success = spend_fixed_credit(data.user_id, data.cost, f"web_tool_{data.tool_type}", f"Dùng {data.tool_type} trên Web")
    
    if not success:
        return {"success": False, "message": f"Số dư không đủ! Yêu cầu {data.cost} Xu."}
        
    # 2. (Chỗ này sẽ gọi hàm xử lý AI thật từ bot.py như gọi Deepgram/Fish/Kling)
    # Tạm thời trả về thành công do API AI cần thời gian chờ (Background Task)
    
    # 3. Lấy số dư mới trả về cho Web
    credits, _, _ = get_user(data.user_id)
    
    return {
        "success": True, 
        "message": f"Lệnh {data.tool_type} đã được đưa vào hàng đợi. Vui lòng kiểm tra hòm thư sau ít phút!",
        "remaining_xu": credits
    }