from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
import hmac
import hashlib
import logging
from config import settings
from db import db_connect, now_text

router = APIRouter()
logger = logging.getLogger("TOAN_AAS_BILLING")

def verify_payos_signature(data: dict, received_sig: str) -> bool:
    if not settings.PAYOS_CHECKSUM_KEY:
        return False
    sorted_keys = sorted([k for k in data.keys() if data[k] is not None and data[k] != ""])
    sign_str = "&".join([f"{k}={data[k]}" for k in sorted_keys])
    
    computed_sig = hmac.new(
        settings.PAYOS_CHECKSUM_KEY.encode('utf-8'),
        sign_str.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(computed_sig, received_sig)

@router.post("/webhook/payos")
async def payos_webhook(request: Request):
    # 1. Bắt ngoại lệ để luôn phản hồi 200 cho PayOS (tránh lỗi 400 "không hoạt động")
    try:
        body = await request.json()
    except:
        return JSONResponse({"success": True, "message": "OK"}, status_code=200)

    # 2. Xử lý logic cộng tiền
    try:
        data = body.get("data", {})
        signature = body.get("signature", "")
        
        # Kiểm tra bảo mật
        if not verify_payos_signature(data, signature):
            return JSONResponse({"success": False, "message": "Sai chữ ký"}, status_code=400)
        
        order_code = str(data.get("orderCode", ""))
        amount = int(data.get("amount", 0))
        
        conn = db_connect()
        c = conn.cursor()
        
        try:
            c.execute("BEGIN IMMEDIATE")
            
            # Check trùng đơn
            c.execute("SELECT 1 FROM payos_processed WHERE order_code=?", (order_code,))
            if c.fetchone():
                conn.rollback()
                return JSONResponse({"success": True, "message": "Đã xử lý rồi"})
                
            # Tìm đơn hàng
            c.execute("SELECT user_id, amount, xu, status FROM payos_orders WHERE order_code=?", (order_code,))
            order = c.fetchone()
            if not order:
                conn.rollback()
                return JSONResponse({"success": False, "message": "Không tìm thấy đơn"})
                
            user_id, expected_amount, expected_xu, status = order
            
            if status != 'PENDING' or expected_amount != amount:
                conn.rollback()
                return JSONResponse({"success": False, "message": "Trạng thái hoặc số tiền sai"})
                
            # Cộng tiền vào database
            c.execute("UPDATE users SET credits = credits + ? WHERE user_id=?", (expected_xu, user_id))
            c.execute("INSERT INTO payos_processed (order_code, processed_at) VALUES (?,?)", (order_code, now_text()))
            c.execute("UPDATE payos_orders SET status='PAID', paid_at=? WHERE order_code=?", (now_text(), order_code))
            
            c.execute("SELECT credits FROM users WHERE user_id=?", (user_id,))
            balance_after = c.fetchone()[0]
            c.execute(
                "INSERT INTO credit_events (user_id, delta, balance_after, event_type, ref_id, note, created_at) VALUES (?,?,?,?,?,?,?)",
                (user_id, expected_xu, balance_after, "payos_deposit", order_code, f"App Nạp: {amount}đ", now_text())
            )
            
            conn.commit()
            return JSONResponse({"success": True, "message": "Cộng Xu thành công"})
        except Exception as db_e:
            conn.rollback()
            logger.error(f"Lỗi DB: {db_e}")
            raise HTTPException(status_code=500, detail="Lỗi xử lý Database")
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Lỗi Webhook: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)