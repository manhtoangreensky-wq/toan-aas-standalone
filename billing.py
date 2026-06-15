from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
import hmac
import hashlib
import logging
import requests
import random
from datetime import datetime, timedelta
from config import settings
from db import db_connect, now_text

router = APIRouter()
logger = logging.getLogger("WEB_BILLING_BRIDGE")

# Gói Storage mặc định theo spec
STORAGE_PACKAGES = {
    "storage_10k": {"amount": 10000, "quota_mb": 100, "days": 30},
    "storage_20k": {"amount": 20000, "quota_mb": 300, "days": 30},
    "storage_50k": {"amount": 50000, "quota_mb": 1024, "days": 30}
}

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
        user_id = str(payload.get("user_id", "guest_unknown"))
        amount = int(payload.get("amount", 0))
        payment_type = payload.get("payment_type", "topup_xu")
        package_id = payload.get("package_id", "")
        
        if amount <= 0:
            return JSONResponse({"success": False, "message": "Số tiền không hợp lệ"}, status_code=400)
            
        order_code = random.randint(100000, 99999999)
        
        # Quy đổi xu tạm tính (chỉ dùng cho topup, storage không cộng xu)
        expected_xu = amount // 100 if payment_type == "topup_xu" else 0
        
        conn = db_connect()
        c = conn.cursor()
        c.execute(
            """INSERT INTO payos_orders 
               (order_code, user_id, amount, xu, status, payment_type, package_id, created_at) 
               VALUES (?, ?, ?, ?, 'PENDING', ?, ?, ?)""",
            (str(order_code), user_id, amount, expected_xu, payment_type, package_id, now_text())
        )
        conn.commit()
        conn.close()
        
        desc_text = f"Nap Xu {order_code}" if payment_type == "topup_xu" else f"Storage {order_code}"
        
        payos_data = {
            "orderCode": order_code,
            "amount": amount,
            "description": desc_text[:25], # PayOS limit 25 chars
            "cancelUrl": "https://app.toanaas.vn/billing/cancel",
            "returnUrl": "https://app.toanaas.vn/billing/return"
        }
        
        payos_data["signature"] = sign_payos_data(payos_data)
        
        headers = {
            "x-client-id": settings.PAYOS_CLIENT_ID,
            "x-api-key": settings.PAYOS_API_KEY,
            "Content-Type": "application/json"
        }
        
        response = requests.post("https://api-merchant.payos.vn/v2/payment-requests", json=payos_data, headers=headers)
        res_json = response.json()
        
        if res_json.get("code") == "00":
            return JSONResponse({
                "success": True,
                "checkoutUrl": res_json["data"]["checkoutUrl"],
                "checkout_url": res_json["data"]["checkoutUrl"], # Support old bot format
                "orderCode": order_code
            })
        else:
            return JSONResponse({"success": False, "message": "Lỗi PayOS"}, status_code=400)
            
    except Exception as e:
        logger.error(f"Lỗi tạo link: {e}")
        return JSONResponse({"success": False, "message": "Lỗi server"}, status_code=500)

@router.post("/webhook/payos")
async def payos_webhook(request: Request):
    try:
        body = await request.json()
    except:
        return JSONResponse({"success": True}, status_code=200)

    try:
        data = body.get("data", {})
        signature = body.get("signature", "")
        
        # Bỏ qua ping test an toàn, trả về 200 HTTP
        if body.get("code") == "00" and str(body.get("desc", "")).lower() == "success":
            if str(data.get("orderCode", "")) in ["123", "", "None"] or body.get("test") == True:
                return JSONResponse({"success": True}, status_code=200)
                
        if not signature or not verify_payos_signature(data, signature):
            return JSONResponse({"success": False, "message": "Sai chữ ký"}, status_code=400)
            
        order_code = str(data.get("orderCode", ""))
        amount = int(data.get("amount", 0))
        
        conn = db_connect()
        c = conn.cursor()
        
        try:
            c.execute("BEGIN IMMEDIATE")
            
            # Idempotency: Khóa trùng lặp
            c.execute("SELECT apply_status FROM payos_processed WHERE order_code=?", (order_code,))
            processed = c.fetchone()
            if processed and processed[0] == 'success':
                conn.rollback()
                return JSONResponse({"success": True, "message": "Đã xử lý"})
                
            # Lấy thông tin đơn hàng gốc
            c.execute("SELECT user_id, amount, status, COALESCE(payment_type, 'topup_xu'), package_id FROM payos_orders WHERE order_code=?", (order_code,))
            order = c.fetchone()
            if not order:
                conn.rollback()
                return JSONResponse({"success": False, "message": "Không tìm thấy đơn"})
                
            user_id, expected_amount, status, payment_type, package_id = order
            
            if status != 'PENDING' or expected_amount != amount:
                conn.rollback()
                return JSONResponse({"success": False, "message": "Sai lệch giao dịch"}, status_code=400)

            c.execute("INSERT OR IGNORE INTO users (user_id, credits, created_at) VALUES (?, 0, ?)", (user_id, now_text()))

            # PHÂN LUỒNG LOGIC KINH DOANH
            if payment_type == "topup_xu":
                # 1 Xu = 100đ
                xu_to_add = amount // 100
                c.execute("UPDATE users SET credits = credits + ? WHERE user_id=?", (xu_to_add, user_id))
                
                c.execute("SELECT credits FROM users WHERE user_id=?", (user_id,))
                balance_after = c.fetchone()[0]
                c.execute(
                    "INSERT INTO credit_events (user_id, delta, balance_after, event_type, ref_id, note, created_at) VALUES (?,?,?,?,?,?,?)",
                    (user_id, xu_to_add, balance_after, "payos_topup", order_code, f"Topup: {amount}đ", now_text())
                )
                apply_status = 'success'

            elif payment_type == "storage_addon":
                if package_id in STORAGE_PACKAGES:
                    pkg = STORAGE_PACKAGES[package_id]
                    starts_at = datetime.now()
                    expires_at = starts_at + timedelta(days=pkg["days"])
                    
                    c.execute("""
                        INSERT INTO storage_entitlements 
                        (user_id, source, payment_order_code, package_id, quota_mb, starts_at, expires_at, created_at) 
                        VALUES (?, 'payos', ?, ?, ?, ?, ?, ?)
                    """, (user_id, order_code, package_id, pkg["quota_mb"], starts_at.strftime("%Y-%m-%d %H:%M:%S"), expires_at.strftime("%Y-%m-%d %H:%M:%S"), now_text()))
                    
                    c.execute("INSERT OR IGNORE INTO storage_usage (user_id, used_bytes, updated_at) VALUES (?, 0, ?)", (user_id, now_text()))
                    
                    c.execute("""
                        INSERT INTO storage_events (user_id, event_type, delta_mb, ref_id, note, created_at) 
                        VALUES (?, 'purchase_addon', ?, ?, ?, ?)
                    """, (user_id, pkg["quota_mb"], order_code, f"Gói: {package_id}", now_text()))
                    
                    apply_status = 'success'
                else:
                    apply_status = 'manual_review'
            else:
                # Unknown payment type -> manual_review, không cộng Xu/Storage
                logger.warning(f"⚠️ PayOS payment_type không xác định. Order: {order_code}, User: {user_id}")
                apply_status = 'manual_review'

            # Chốt trạng thái
            c.execute("UPDATE payos_orders SET status='PAID', paid_at=? WHERE order_code=?", (now_text(), order_code))
            c.execute("INSERT INTO payos_processed (order_code, payment_type, apply_status, processed_at) VALUES (?, ?, ?, ?)", 
                      (order_code, payment_type, apply_status, now_text()))
            
            conn.commit()
            return JSONResponse({"success": True, "status": apply_status})
            
        except Exception as db_e:
            conn.rollback()
            logger.error(f"Lỗi DB: {db_e}")
            raise HTTPException(status_code=500, detail="Database Error")
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Lỗi Webhook tổng: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)