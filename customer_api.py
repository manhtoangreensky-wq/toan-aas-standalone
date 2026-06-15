from fastapi import APIRouter
from pydantic import BaseModel
import logging
import random
from db import db_connect, now_text

router = APIRouter()
logger = logging.getLogger("TOAN_AAS_CUSTOMER_API")

class FeedbackReq(BaseModel):
    user_id: str
    content: str

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
    except Exception as e:
        return {"success": False, "message": "Lỗi hệ thống khi lưu góp ý."}
    finally: conn.close()

class PayosReq(BaseModel): user_id: str; amount_vnd: int; xu_nhan: int
@router.post("/payos/create-link")
async def create_web_payos_link(data: PayosReq):
    # Trả về URL thanh toán giả lập để Web không sập (Sếp có thể nối hàm PayOS thực sau)
    return {"success": True, "checkout_url": f"https://payos.vn/mock-checkout?amount={data.amount_vnd}"}

class AIToolReq(BaseModel): user_id: str; tool_type: str; cost: int; prompt: str
@router.post("/ai/process")
async def process_ai_tool(data: AIToolReq):
    conn = db_connect(); c = conn.cursor()
    try:
        c.execute("BEGIN IMMEDIATE")
        c.execute("SELECT credits FROM users WHERE user_id=?", (data.user_id,))
        user = c.fetchone()
        if not user:
            conn.rollback(); return {"success": False, "message": "Lỗi xác thực!"}
        current_credits = user[0]
        if current_credits < data.cost:
            conn.rollback(); return {"success": False, "message": f"Số dư không đủ! Cần {data.cost} Xu."}
        
        new_credits = current_credits - data.cost
        c.execute("UPDATE users SET credits = ? WHERE user_id=?", (new_credits, data.user_id))
        c.execute("INSERT INTO credit_events (user_id, delta, balance_after, event_type, note, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                  (data.user_id, -data.cost, new_credits, f"web_tool_{data.tool_type}", f"Dùng {data.tool_type} trên Web", now_text()))
        conn.commit()
        return {"success": True, "message": f"Lệnh {data.tool_type} đã vào hàng đợi!", "remaining_xu": new_credits}
    except Exception as e:
        conn.rollback(); return {"success": False, "message": "Lỗi xử lý."}
    finally: conn.close()

# API PORTAL CÁ NHÂN
@router.get("/portal/projects/{user_id}")
async def customer_projects(user_id: str):
    conn = db_connect(); c = conn.cursor()
    c.execute("SELECT username FROM users WHERE user_id=?", (user_id,))
    u = c.fetchone()
    if not u: return {"success": False, "data": []}
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