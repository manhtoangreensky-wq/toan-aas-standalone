from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
import hmac
import hashlib
import logging
import requests
import random
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

def sign_payos_data(data: dict) -> str:
    sorted_keys = sorted([k for k in data.keys() if data[k] is not None and data[k] != ""])
    sign_str = "&".join([f"{k}={data[k]}" for k in sorted_keys])
    return hmac.new(
        settings.PAYOS_CHECKSUM_KEY.encode('utf-8'),
        sign_str.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

@router.post("/create-payment-link")
async def create_payment_link(payload: dict):
    try:
        user_id = str(payload.get("user_id", "guest_web"))
        amount = int(payload.get("amount", 50000))
        
        order_code = random.randint(100000, 99999999)
        
        conn = db_connect()
        c = conn.cursor()
        c.execute(
            "INSERT INTO payos_orders (order_code, user_id, amount, xu, status, created_at) VALUES (?, ?, ?, ?, 'PENDING', ?)",
            (str(order_code), user_id, amount, amount, now_text())
        )
        conn.commit()
        conn.close()
        
        payos_data = {
            "orderCode": order_code,
            "amount": amount,
            "description": f"Nap xu {order_code}",
            "cancelUrl": "https://app.toanaas.vn/wallet-app",
            "returnUrl": "https://app.toanaas.vn/wallet-app"
        }
        
        payos_data["signature"] = sign_payos_data(payos_data)
        
        headers = {
            "x-client-id": settings.PAYOS_CLIENT_ID,
            "x-api-key": settings.PAYOS_API_KEY,
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            "https://api-merchant.payos.vn/v2/payment-requests",
            json=payos_data,
            headers=headers
        )
        res_json = response.json()
        
        if res_json.get("code") == "00":
            return JSONResponse({
                "success": True,
                "checkoutUrl": res_json["data"]["checkoutUrl"],
                "orderCode": order_code
            })
        else:
            return JSONResponse({
                "success": False,
                "message": res_json.get("desc", "Lỗi tạo link từ PayOS")
            }, status_code=400)
            
    except Exception as e:
        logger.error(f"Lỗi hệ thống tạo link: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)

@router.post("/webhook/payos")
async def payos_webhook(request: Request):
    try:
        body = await request.json()
    except:
        return JSONResponse({"success": True}, status_code=200)

    try:
        data = body.get("data")
        # Xử lý an toàn khi PayOS gửi dữ liệu Test rỗng
        if data is None:
            data = {}
            
        signature = body.get("signature", "")
        order_code = str(data.get("orderCode", ""))
        amount = int(data.get("amount", 0))
        
        # --- LỐI ĐI VIP CHO LỆNH TEST TỪ PAYOS ---
        # Khi bấm nút "Lưu" trên trang PayOS, nó sẽ gửi một lệnh ảo. Ta cho qua luôn bằng lệnh này!
        if not order_code or order_code == "123" or body.get("desc") == "success" or not signature:
            return JSONResponse({"success": True, "message": "Webhook Test OK"}, status_code=200)
        
        # Kiểm tra bảo mật cho các giao dịch thật
        if not verify_payos_signature(data, signature):
            return JSONResponse({"success": False, "message": "Sai chữ ký"}, status_code=400)
        
        conn = db_connect()
        c = conn.cursor()
        
        try:
            c.execute("BEGIN IMMEDIATE")
            
            c.execute("SELECT 1 FROM payos_processed WHERE order_code=?", (order_code,))
            if c.fetchone():
                conn.rollback()
                return JSONResponse({"success": True, "message": "Đã xử lý đơn này rồi"})
                
            c.execute("SELECT user_id, amount, xu, status FROM payos_orders WHERE order_code=?", (order_code,))
            order = c.fetchone()
            if not order:
                conn.rollback()
                return JSONResponse({"success": False, "message": "Không tìm thấy mã đơn hàng"})
                
            user_id, expected_amount, expected_xu, status = order
            
            if status != 'PENDING' or expected_amount != amount:
                conn.rollback()
                return JSONResponse({"success": False, "message": "Sai lệch số tiền hoặc trạng thái đơn"})
                
            # Tạo tài khoản ví tự động cho người dùng mới / khách vãng lai
            c.execute("INSERT OR IGNORE INTO users (user_id, credits, created_at) VALUES (?, 0, ?)", (user_id, now_text()))
            c.execute("UPDATE users SET credits = credits + ? WHERE user_id=?", (expected_xu, user_id))
            c.execute("INSERT INTO payos_processed (order_code, processed_at) VALUES (?,?)", (order_code, now_text()))
            c.execute("UPDATE payos_orders SET status='PAID', paid_at=? WHERE order_code=?", (now_text(), order_code))
            
            c.execute("SELECT credits FROM users WHERE user_id=?", (user_id,))
            balance_after = c.fetchone()[0]
            c.execute(
                "INSERT INTO credit_events (user_id, delta, balance_after, event_type, ref_id, note, created_at) VALUES (?,?,?,?,?,?,?)",
                (user_id, expected_xu, balance_after, "payos_deposit", order_code, f"Nạp qua PayOS: {amount}đ", now_text())
            )
            
            conn.commit()
            return JSONResponse({"success": True, "message": "Cộng Xu thành công"})
        except Exception as db_e:
            conn.rollback()
            logger.error(f"Lỗi xử lý DB: {db_e}")
            raise HTTPException(status_code=500, detail="Lỗi xử lý Database")
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Lỗi Webhook: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)