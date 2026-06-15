from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging
from db import db_connect, now_text

router = APIRouter()
logger = logging.getLogger("TOAN_AAS_ERP")

# --- 1. AUTO-BUILDER (Khởi tạo Database) ---
def init_erp_database():
    conn = db_connect()
    c = conn.cursor()
    try:
        c.execute("BEGIN IMMEDIATE")
        c.execute('''CREATE TABLE IF NOT EXISTS erp_customers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, email TEXT, type TEXT DEFAULT 'Tiềm năng', source TEXT, created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS erp_projects (id INTEGER PRIMARY KEY AUTOINCREMENT, project_name TEXT, customer_name TEXT, budget INTEGER, status TEXT DEFAULT 'Đang triển khai', created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS erp_inventory (id INTEGER PRIMARY KEY AUTOINCREMENT, item_code TEXT, item_name TEXT, category TEXT, quantity INTEGER, unit_price INTEGER, created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS erp_transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, trans_type TEXT, amount INTEGER, category TEXT, note TEXT, created_at TEXT)''')
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Lỗi khởi tạo ERP: {e}")
    finally:
        conn.close()

init_erp_database()

# --- 2. API THỐNG KÊ TỔNG QUAN ---
@router.get("/dashboard-stats")
async def get_erp_stats():
    conn = db_connect()
    c = conn.cursor()
    try:
        c.execute("SELECT COUNT(*) FROM erp_customers")
        total_customers = c.fetchone()[0] or 0
        c.execute("SELECT COUNT(*), SUM(budget) FROM erp_projects")
        proj_data = c.fetchone()
        total_projects = proj_data[0] or 0
        total_revenue = proj_data[1] or 0
        return {"success": True, "data": {"total_users": total_customers, "total_revenue": total_revenue, "total_projects": total_projects}}
    finally:
        conn.close()

# --- 3. API CRM & DỰ ÁN (Đã có) ---
class CustomerReq(BaseModel): name: str; phone: str; type: str
@router.post("/customers")
async def add_customer(data: CustomerReq):
    conn = db_connect(); c = conn.cursor()
    c.execute("INSERT INTO erp_customers (name, phone, type, created_at) VALUES (?, ?, ?, ?)", (data.name, data.phone, data.type, now_text()))
    conn.commit(); conn.close()
    return {"success": True, "message": "Đã thêm Khách hàng mới!"}

@router.get("/customers")
async def get_customers():
    conn = db_connect(); c = conn.cursor()
    c.execute("SELECT id, name, phone, type, created_at FROM erp_customers ORDER BY id DESC")
    data = [{"id": r[0], "name": r[1], "phone": r[2], "type": r[3], "created_at": r[4]} for r in c.fetchall()]
    conn.close()
    return {"success": True, "data": data}

class ProjectReq(BaseModel): project_name: str; customer_name: str; budget: int; status: str
@router.post("/projects")
async def add_project(data: ProjectReq):
    conn = db_connect(); c = conn.cursor()
    c.execute("INSERT INTO erp_projects (project_name, customer_name, budget, status, created_at) VALUES (?, ?, ?, ?, ?)", (data.project_name, data.customer_name, data.budget, data.status, now_text()))
    conn.commit(); conn.close()
    return {"success": True, "message": "Đã tạo Dự án!"}

@router.get("/projects")
async def get_projects():
    conn = db_connect(); c = conn.cursor()
    c.execute("SELECT id, project_name, customer_name, budget, status, created_at FROM erp_projects ORDER BY id DESC")
    data = [{"id": r[0], "project_name": r[1], "customer_name": r[2], "budget": r[3], "status": r[4], "created_at": r[5]} for r in c.fetchall()]
    conn.close()
    return {"success": True, "data": data}

# --- 4. API KHO HÀNG (MỚI) ---
class InventoryReq(BaseModel): item_code: str; item_name: str; category: str; quantity: int; unit_price: int
@router.post("/inventory")
async def add_inventory(data: InventoryReq):
    conn = db_connect(); c = conn.cursor()
    c.execute("INSERT INTO erp_inventory (item_code, item_name, category, quantity, unit_price, created_at) VALUES (?, ?, ?, ?, ?, ?)", 
              (data.item_code, data.item_name, data.category, data.quantity, data.unit_price, now_text()))
    conn.commit(); conn.close()
    return {"success": True, "message": "Đã nhập kho thành công!"}

@router.get("/inventory")
async def get_inventory():
    conn = db_connect(); c = conn.cursor()
    c.execute("SELECT id, item_code, item_name, category, quantity, unit_price FROM erp_inventory ORDER BY id DESC")
    data = [{"id": r[0], "item_code": r[1], "item_name": r[2], "category": r[3], "quantity": r[4], "unit_price": r[5]} for r in c.fetchall()]
    conn.close()
    return {"success": True, "data": data}

# --- 5. API THU CHI (MỚI) ---
class FinanceReq(BaseModel): trans_type: str; amount: int; category: str; note: str
@router.post("/finance")
async def add_finance(data: FinanceReq):
    conn = db_connect(); c = conn.cursor()
    c.execute("INSERT INTO erp_transactions (trans_type, amount, category, note, created_at) VALUES (?, ?, ?, ?, ?)", 
              (data.trans_type, data.amount, data.category, data.note, now_text()))
    conn.commit(); conn.close()
    return {"success": True, "message": "Đã ghi nhận giao dịch!"}

@router.get("/finance")
async def get_finance():
    conn = db_connect(); c = conn.cursor()
    c.execute("SELECT id, trans_type, amount, category, note, created_at FROM erp_transactions ORDER BY id DESC")
    data = [{"id": r[0], "trans_type": r[1], "amount": r[2], "category": r[3], "note": r[4], "created_at": r[5]} for r in c.fetchall()]
    conn.close()
    return {"success": True, "data": data}