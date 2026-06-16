from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import hmac
import hashlib
import logging
import requests
import random
import os
from datetime import datetime, timedelta
from config import settings
from db import db_connect, now_text
from security import admin_guard_response

router = APIRouter()
logger = logging.getLogger("WEB_BILLING_BRIDGE")

STORAGE_PACKAGES = {
    "storage_10k": {"amount": 10000, "quota_mb": 50, "days": 30},
    "storage_20k": {"amount": 20000, "quota_mb": 100, "days": 30},
    "storage_50k": {"amount": 50000, "quota_mb": 250, "days": 30},
    "storage_100k": {"amount": 100000, "quota_mb": 500, "days": 30},
}

# ========================================================
# AUTO-HEALING DATABASE: Tự động đắp cột nếu Database bị thiếu
# ========================================================
def auto_repair_db():
    conn = db_connect()
    c = conn.cursor()
    try:
        c.execute("BEGIN IMMEDIATE")
        c.execute('''CREATE TABLE IF NOT EXISTS payos_processed (order_code TEXT PRIMARY KEY, payment_type TEXT, apply_status TEXT, processed_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS payos_orders (order_code TEXT PRIMARY KEY, user_id TEXT, amount INTEGER, xu INTEGER, status TEXT, payment_type TEXT DEFAULT 'topup_xu', package_id TEXT, created_at TEXT, paid_at TEXT)''')
        for table_name, column_name, column_sql in [
            ("payos_orders", "payment_type", "payment_type TEXT DEFAULT 'topup_xu'"),
            ("payos_orders", "package_id", "package_id TEXT"),
            ("payos_processed", "payment_type", "payment_type TEXT"),
            ("payos_processed", "apply_status", "apply_status TEXT"),
        ]:
            c.execute(f"PRAGMA table_info({table_name})")
            existing = {row[1] for row in c.fetchall()}
            if column_name not in existing:
                c.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}")
        c.execute('''CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, credits INTEGER DEFAULT 0, created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS credit_events (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, delta INTEGER, balance_after INTEGER, event_type TEXT, ref_id TEXT, note TEXT, created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS storage_entitlements (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, source TEXT, payment_order_code TEXT, package_id TEXT, quota_mb INTEGER, starts_at TEXT, expires_at TEXT, status TEXT DEFAULT 'active', created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS storage_usage (user_id TEXT PRIMARY KEY, used_bytes INTEGER DEFAULT 0, updated_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS storage_events (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, event_type TEXT, delta_mb INTEGER, used_bytes_after INTEGER, ref_id TEXT, note TEXT, created_at TEXT)''')
        conn.commit()
    except Exception as e:
        conn.rollback()
        print("Lỗi khi tự động vá DB:", e)
    finally:
        conn.close()

# Chạy kích hoạt vá DB ngay lập tức
auto_repair_db()

# ========================================================

def sign_payos_data(data: dict) -> str:
    if not settings.PAYOS_CHECKSUM_KEY:
        raise ValueError("Thiếu PAYOS_CHECKSUM_KEY")
    sorted_keys = sorted([k for k in data.keys() if data[k] is not None and data[k] != ""])
    sign_str = "&".join([f"{k}={data[k]}" for k in sorted_keys])
    return hmac.new(
        settings.PAYOS_CHECKSUM_KEY.encode('utf-8'),
        sign_str.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

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

@router.post("/create-payment-link")
async def create_payment_link(payload: dict):
    try:
        # Bắt lỗi số 1: Thiếu cấu hình Key trên Railway
        if not settings.PAYOS_CLIENT_ID or not settings.PAYOS_API_KEY or not settings.PAYOS_CHECKSUM_KEY:
            return JSONResponse({"success": False, "message": "CHÚ Ý: Sếp chưa điền đủ 3 Mã Key của cổng PayOS vào Variables trên Railway!"}, status_code=400)

        user_id = str(payload.get("user_id", "guest_unknown"))
        amount = int(payload.get("amount", 0))
        payment_type = payload.get("payment_type", "topup_xu")
        package_id = payload.get("package_id", "CUSTOM_TOPUP")

        if payment_type == "storage_addon":
            package = STORAGE_PACKAGES.get(str(package_id))
            if not package:
                return JSONResponse({"success": False, "message": "Gói dung lượng không hợp lệ."}, status_code=400)
            amount = int(package["amount"])
        
        if amount <= 0:
            return JSONResponse({"success": False, "message": "Số tiền gửi lên không hợp lệ."}, status_code=400)
            
        order_code = random.randint(100000, 99999999)
        expected_xu = amount // 100 if payment_type == "topup_xu" else 0
        
        # Bắt lỗi số 2: Lỗi ghi vào cơ sở dữ liệu
        try:
            conn = db_connect()
            c = conn.cursor()
            c.execute(
                """INSERT INTO payos_orders 
                   (order_code, user_id, amount, xu, status, payment_type, package_id, created_at) 
                   VALUES (?, ?, ?, ?, 'PENDING', ?, ?, ?)""",
                (str(order_code), user_id, amount, expected_xu, payment_type, package_id, now_text())
            )
            conn.commit()
        except Exception as db_err:
            conn.rollback()
            return JSONResponse({"success": False, "message": f"LỖI DATABASE: {str(db_err)}"}, status_code=500)
        finally:
            conn.close()
            
        desc_text = f"Nap Xu {order_code}" if payment_type == "topup_xu" else f"Storage {order_code}"
        
        public_base_url = os.environ.get("PUBLIC_BASE_URL", "https://app.toanaas.vn").rstrip("/")
        payos_data = {
            "orderCode": order_code,
            "amount": amount,
            "description": desc_text[:25],
            "cancelUrl": f"{public_base_url}/wallet-app",
            "returnUrl": f"{public_base_url}/wallet-app"
        }
        
        # Bắt lỗi số 3: Lỗi thuật toán sinh mã
        try:
            payos_data["signature"] = sign_payos_data(payos_data)
        except Exception as sig_err:
            return JSONResponse({"success": False, "message": f"LỖI KÝ MÃ BẢO MẬT: {str(sig_err)}"}, status_code=500)
        
        headers = {
            "x-client-id": settings.PAYOS_CLIENT_ID,
            "x-api-key": settings.PAYOS_API_KEY,
            "Content-Type": "application/json"
        }
        
        # Bắt lỗi số 4: Lỗi PayOS từ chối giao dịch
        response = requests.post("https://api-merchant.payos.vn/v2/payment-requests", json=payos_data, headers=headers)
        res_json = response.json()
        
        if res_json.get("code") == "00":
            return JSONResponse({
                "success": True,
                "checkoutUrl": res_json["data"]["checkoutUrl"],
                "checkout_url": res_json["data"]["checkoutUrl"], 
                "orderCode": order_code
            })
        else:
            return JSONResponse({"success": False, "message": f"PAYOS TỪ CHỐI: {res_json.get('desc')}"}, status_code=400)
            
    except Exception as e:
        logger.error(f"Lỗi tạo link: {e}")
        return JSONResponse({"success": False, "message": f"LỖI HỆ THỐNG PYTHON: {str(e)}"}, status_code=500)

@router.post("/webhook/payos")
async def payos_webhook(request: Request):
    try:
        body = await request.json()
    except:
        return JSONResponse({"success": True}, status_code=200)

    try:
        data = body.get("data", {})
        signature = body.get("signature", "")
        
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
            c.execute("SELECT apply_status FROM payos_processed WHERE order_code=?", (order_code,))
            processed = c.fetchone()
            if processed and processed[0] == 'success':
                conn.rollback()
                return JSONResponse({"success": True, "message": "Đã xử lý"})
                
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

            if payment_type == "topup_xu":
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
                package = STORAGE_PACKAGES.get(str(package_id))
                if not package:
                    conn.rollback()
                    return JSONResponse({"success": False, "message": "Gói dung lượng không hợp lệ"}, status_code=400)
                starts_at = now_text()
                expires_at = (datetime.now() + timedelta(days=int(package["days"]))).strftime("%Y-%m-%d %H:%M:%S")
                c.execute("INSERT OR IGNORE INTO storage_usage (user_id, used_bytes, updated_at) VALUES (?, 0, ?)", (user_id, now_text()))
                c.execute(
                    """INSERT INTO storage_entitlements
                       (user_id, source, payment_order_code, package_id, quota_mb, starts_at, expires_at, status, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?)""",
                    (user_id, "payos_storage_addon", order_code, package_id, int(package["quota_mb"]), starts_at, expires_at, now_text())
                )
                c.execute("SELECT used_bytes FROM storage_usage WHERE user_id=?", (user_id,))
                used_after = int((c.fetchone() or [0])[0] or 0)
                c.execute(
                    "INSERT INTO storage_events (user_id, event_type, delta_mb, used_bytes_after, ref_id, note, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (user_id, "storage_addon_paid", int(package["quota_mb"]), used_after, order_code, f"Storage add-on {package_id}", now_text())
                )
                apply_status = 'success'
            else:
                apply_status = 'manual_review'

            c.execute("UPDATE payos_orders SET status='PAID', paid_at=? WHERE order_code=?", (now_text(), order_code))
            c.execute("INSERT INTO payos_processed (order_code, payment_type, apply_status, processed_at) VALUES (?, ?, ?, ?)", (order_code, payment_type, apply_status, now_text()))
            
            conn.commit()
            return JSONResponse({"success": True, "status": apply_status})
        except Exception as db_e:
            conn.rollback()
            return JSONResponse({"success": False, "message": f"Lỗi DB Webhook: {str(db_e)}"}, status_code=500)
        finally:
            conn.close()
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.get("/storage/packages")
async def storage_packages():
    return {"success": True, "base_free_mb": 50, "data": STORAGE_PACKAGES}


@router.get("/storage/status/{user_id}")
async def storage_status(user_id: str):
    conn = db_connect()
    c = conn.cursor()
    try:
        now = now_text()
        c.execute("INSERT OR IGNORE INTO storage_usage (user_id, used_bytes, updated_at) VALUES (?, 0, ?)", (user_id, now))
        c.execute("SELECT used_bytes FROM storage_usage WHERE user_id=?", (user_id,))
        used_bytes = int((c.fetchone() or [0])[0] or 0)
        c.execute(
            """SELECT COALESCE(SUM(quota_mb), 0) FROM storage_entitlements
               WHERE user_id=? AND status='active' AND (expires_at IS NULL OR expires_at >= ?)""",
            (user_id, now)
        )
        paid_mb = int((c.fetchone() or [0])[0] or 0)
        total_mb = 50 + paid_mb
        conn.commit()
        return {
            "success": True,
            "user_id": user_id,
            "base_free_mb": 50,
            "paid_quota_mb": paid_mb,
            "total_quota_mb": total_mb,
            "used_bytes": used_bytes,
            "used_mb": round(used_bytes / 1024 / 1024, 2),
            "remaining_mb": max(0, round(total_mb - used_bytes / 1024 / 1024, 2)),
        }
    finally:
        conn.close()


class StorageGrantReq(BaseModel):
    admin_id: str
    user_id: str
    package_id: str
    note: str = ""


@router.post("/storage/admin/grant")
async def admin_grant_storage(data: StorageGrantReq):
    denied = admin_guard_response(data.admin_id)
    if denied:
        return denied
    package = STORAGE_PACKAGES.get(str(data.package_id))
    if not package:
        return {"success": False, "message": "Gói dung lượng không hợp lệ."}
    conn = db_connect()
    c = conn.cursor()
    try:
        starts_at = now_text()
        expires_at = (datetime.now() + timedelta(days=int(package["days"]))).strftime("%Y-%m-%d %H:%M:%S")
        c.execute("BEGIN IMMEDIATE")
        c.execute("INSERT OR IGNORE INTO storage_usage (user_id, used_bytes, updated_at) VALUES (?, 0, ?)", (data.user_id, now_text()))
        c.execute(
            """INSERT INTO storage_entitlements
               (user_id, source, payment_order_code, package_id, quota_mb, starts_at, expires_at, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?)""",
            (data.user_id, "admin_grant", None, data.package_id, int(package["quota_mb"]), starts_at, expires_at, now_text())
        )
        c.execute("SELECT used_bytes FROM storage_usage WHERE user_id=?", (data.user_id,))
        used_after = int((c.fetchone() or [0])[0] or 0)
        c.execute(
            "INSERT INTO storage_events (user_id, event_type, delta_mb, used_bytes_after, ref_id, note, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (data.user_id, "storage_addon_admin_grant", int(package["quota_mb"]), used_after, data.admin_id, data.note or f"Admin grant {data.package_id}", now_text())
        )
        conn.commit()
        return {"success": True, "message": f"Đã tặng +{package['quota_mb']}MB/tháng cho user."}
    except Exception:
        conn.rollback()
        return {"success": False, "message": "Không thể tặng dung lượng lúc này."}
    finally:
        conn.close()
