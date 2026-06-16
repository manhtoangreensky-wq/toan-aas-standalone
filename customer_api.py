from fastapi import APIRouter
from pydantic import BaseModel
import logging
import os
from db import db_connect, now_text

# Kéo các hàm "vũ khí hạng nặng" từ bot.py của sếp sang để chạy PayOS chuẩn 100%
from bot import generate_order_code, create_order, create_payos_payment_request

router = APIRouter()
logger = logging.getLogger("TOAN_AAS_CUSTOMER_API")

# --- AUTO CREATE TABLE CHO NẠP THỦ CÔNG ---
def init_manual_db():
    conn = db_connect()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS manual_orders 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, username TEXT, 
                 amount INTEGER, xu_expected INTEGER, txid TEXT, method TEXT, status TEXT DEFAULT 'pending', created_at TEXT)''')
    conn.commit()
    conn.close()

init_manual_db()

# --- 1. API GỬI GÓP Ý ---
class FeedbackReq(BaseModel): user_id: str; content: str
@router.post("/feedback")
async def submit_feedback(data: FeedbackReq):
    conn = db_connect(); c = conn.cursor()
    try:
        c.execute("SELECT username FROM users WHERE user_id=?", (str(data.user_id),))
        row = c.fetchone()
        username = row[0] if row else "Unknown"
        c.execute("CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, username TEXT, content TEXT, timestamp TEXT)")
        c.execute("INSERT INTO feedback (user_id, username, content, timestamp) VALUES (?, ?, ?, ?)", (str(data.user_id), username, data.content, now_text()))
        conn.commit()
        return {"success": True, "message": "Góp ý đã được gửi tới Ban Giám Đốc!"}
    except Exception as e: return {"success": False, "message": "Lỗi hệ thống."}
    finally: conn.close()

# --- 2. API PAYOS (KẾT NỐI HÀM CHUẨN CỦA BOT.PY) ---
class PayosReq(BaseModel): user_id: str; amount_vnd: int; xu_nhan: int
@router.post("/payos/create-link")
async def create_web_payos_link(data: PayosReq):
    try:
        # 1. Tạo order code bằng hàm chuẩn
        order_code = generate_order_code()
        
        # 2. Lưu vào DB chờ webhook đối soát
        create_order(order_code, data.user_id, data.amount_vnd, data.xu_nhan)
        
        # 3. Gọi hàm request chuẩn xác của sếp
        return_url = os.environ.get("PUBLIC_BASE_URL", "https://app.toanaas.vn").rstrip("/") + "/"
        
        payos_body = {
            "orderCode": order_code,
            "amount": data.amount_vnd,
            "description": f"AAS {data.user_id} {data.xu_nhan}XU"[:25],
            "returnUrl": return_url,
            "cancelUrl": return_url
        }
        
        res, res_data, raw_preview, raw_str = await create_payos_payment_request(payos_body)
        
        if res_data and res_data.get("code") == "00":
            return {"success": True, "checkout_url": res_data["data"]["checkoutUrl"]}
        else:
            logger.error(f"Lỗi trả về từ PayOS: {res_data}")
            return {"success": False, "message": "Cổng PayOS từ chối yêu cầu. Vui lòng thử Nạp Thủ Công."}
            
    except Exception as e:
        logger.error(f"Lỗi try/except PayOS: {e}")
        return {"success": False, "message": "Lỗi mạng kết nối PayOS. Vui lòng thử Nạp Thủ Công."}

# --- 3. API NẠP THỦ CÔNG (GỬI YÊU CẦU) ---
class ManualTopupReq(BaseModel): user_id: str; amount: int; xu_expected: int; txid: str; method: str
@router.post("/manual-topup")
async def submit_manual_topup(data: ManualTopupReq):
    conn = db_connect(); c = conn.cursor()
    try:
        c.execute("SELECT username FROM users WHERE user_id=?", (str(data.user_id),))
        row = c.fetchone()
        username = row[0] if row else "Unknown"
        
        c.execute("SELECT id FROM manual_orders WHERE txid=?", (data.txid,))
        if c.fetchone(): return {"success": False, "message": "Mã giao dịch (TxID) này đã được gửi trước đó!"}
            
        c.execute("INSERT INTO manual_orders (user_id, username, amount, xu_expected, txid, method, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (data.user_id, username, data.amount, data.xu_expected, data.txid, data.method, now_text()))
        conn.commit()
        return {"success": True, "message": "Đã gửi yêu cầu nạp tiền! Vui lòng chờ Admin duyệt."}
    except Exception as e: return {"success": False, "message": "Lỗi hệ thống."}
    finally: conn.close()

# --- 4. API DÀNH CHO ADMIN DUYỆT ĐƠN NẠP ---
@router.get("/admin/manual-orders")
async def get_manual_orders():
    conn = db_connect(); c = conn.cursor()
    c.execute("SELECT id, user_id, username, amount, xu_expected, txid, method, status, created_at FROM manual_orders ORDER BY id DESC")
    data = [{"id": r[0], "user_id": r[1], "username": r[2], "amount": r[3], "xu": r[4], "txid": r[5], "method": r[6], "status": r[7], "date": r[8]} for r in c.fetchall()]
    conn.close()
    return {"success": True, "data": data}

class ApproveReq(BaseModel): order_id: int; action: str
@router.post("/admin/approve-topup")
async def approve_manual_topup(data: ApproveReq):
    conn = db_connect(); c = conn.cursor()
    try:
        c.execute("BEGIN IMMEDIATE")
        c.execute("SELECT user_id, amount, xu_expected, status, txid FROM manual_orders WHERE id=?", (data.order_id,))
        order = c.fetchone()
        if not order or order[3] != 'pending':
            conn.rollback(); return {"success": False, "message": "Đơn không tồn tại hoặc đã được xử lý!"}
            
        user_id, amount, xu_expected, status, txid = order
        
        if data.action == 'approve':
            c.execute("UPDATE manual_orders SET status='approved' WHERE id=?", (data.order_id,))
            c.execute("SELECT credits FROM users WHERE user_id=?", (user_id,))
            current_credits = c.fetchone()[0]
            new_credits = current_credits + xu_expected
            c.execute("UPDATE users SET credits=? WHERE user_id=?", (new_credits, user_id))
            c.execute("INSERT INTO credit_events (user_id, delta, balance_after, event_type, note, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                      (user_id, xu_expected, new_credits, "manual_deposit", f"Duyệt nạp thủ công TxID: {txid}", now_text()))
            msg = f"Đã duyệt +{xu_expected} Xu thành công!"
        else:
            c.execute("UPDATE manual_orders SET status='rejected' WHERE id=?", (data.order_id,))
            msg = "Đã từ chối đơn nạp."
            
        conn.commit()
        return {"success": True, "message": msg}
    except Exception as e:
        conn.rollback(); return {"success": False, "message": "Lỗi xử lý."}
    finally: conn.close()

# --- 5. API AI & PORTAL CÁ NHÂN ---
class AIToolReq(BaseModel): user_id: str; tool_type: str; cost: int; prompt: str
@router.post("/ai/process")
async def process_ai_tool(data: AIToolReq):
    conn = db_connect(); c = conn.cursor()
    try:
        c.execute("BEGIN IMMEDIATE")
        admin_ids_str = os.environ.get("ADMIN_IDS", os.environ.get("ADMIN_ID", ""))
        admin_ids = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip().isdigit()]
        is_admin = int(data.user_id) in admin_ids if data.user_id.isdigit() else False
        
        c.execute("SELECT credits FROM users WHERE user_id=?", (data.user_id,))
        user = c.fetchone()
        if not user: conn.rollback(); return {"success": False, "message": "Lỗi xác thực!"}
        current_credits = user[0]
        
        if is_admin:
            new_credits = current_credits
            delta = 0
            note = f"[ADMIN FREE] Dùng {data.tool_type} trên Web"
        else:
            if current_credits < data.cost:
                conn.rollback(); return {"success": False, "message": f"Số dư không đủ! Cần {data.cost} Xu."}
            new_credits = current_credits - data.cost
            delta = -data.cost
            note = f"Dùng {data.tool_type} trên Web"
            
        c.execute("UPDATE users SET credits = ? WHERE user_id=?", (new_credits, data.user_id))
        c.execute("INSERT INTO credit_events (user_id, delta, balance_after, event_type, note, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                  (data.user_id, delta, new_credits, f"web_tool_{data.tool_type}", note, now_text()))
        conn.commit()
        return {"success": True, "message": f"Lệnh {data.tool_type} đã vào hàng đợi!", "remaining_xu": new_credits}
    except Exception as e: conn.rollback(); return {"success": False, "message": "Lỗi xử lý nội bộ."}
    finally: conn.close()

@router.get("/portal/projects/{user_id}")
async def customer_projects(user_id: str):
    conn = db_connect(); c = conn.cursor()
    c.execute("SELECT username FROM users WHERE user_id=?", (user_id,))
    u = c.fetchone()
    if not u: conn.close(); return {"success": False, "data": []}
    c.execute("SELECT project_name, budget, status, created_at FROM erp_projects WHERE customer_name LIKE ? ORDER BY id DESC", (f"%{u[0]}%",))
    data = [{"name": r[0], "budget": r[1], "status": r[2], "date": r[3].split(' ')[0]} for r in c.fetchall()]
    conn.close(); return {"success": True, "data": data}

@router.get("/portal/affiliates/{user_id}")
async def customer_affiliates(user_id: str):
    conn = db_connect(); c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS affiliate_links (id INTEGER PRIMARY KEY, owner_id TEXT, network TEXT, product_name TEXT, url TEXT, commission_rate INTEGER)")
    c.execute("SELECT network, product_name, url, commission_rate FROM affiliate_links WHERE owner_id=? ORDER BY id DESC", (user_id,))
    data = [{"network": r[0], "product": r[1], "url": r[2], "rate": r[3]} for r in c.fetchall()]
    conn.close(); return {"success": True, "data": data}
    
@router.get("/portal/history/{user_id}")
async def customer_history(user_id: str):
    conn = db_connect(); c = conn.cursor()
    c.execute("SELECT delta, event_type, note, created_at FROM credit_events WHERE user_id=? ORDER BY id DESC LIMIT 15", (user_id,))
    data = [{"delta": r[0], "type": r[1], "note": r[2], "date": r[3]} for r in c.fetchall()]
    conn.close(); return {"success": True, "data": data}