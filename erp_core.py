from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging
from db import db_connect, now_text
import random

router = APIRouter()
logger = logging.getLogger("TOAN_AAS_ERP")

# --- 1. AUTO-BUILDER (Khởi tạo Database) ---
def init_erp_database():
    conn = db_connect()
    c = conn.cursor()
    try:
        c.execute("BEGIN IMMEDIATE")
        # Các bảng cũ (CRM, Dự án, Kho, Thu Chi, Nhân sự, Chấm công, Bán hàng, Tài sản)
        c.execute('''CREATE TABLE IF NOT EXISTS erp_customers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, email TEXT, type TEXT DEFAULT 'Tiềm năng', source TEXT, created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS erp_projects (id INTEGER PRIMARY KEY AUTOINCREMENT, project_name TEXT, customer_name TEXT, budget INTEGER, status TEXT DEFAULT 'Đang triển khai', created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS erp_inventory (id INTEGER PRIMARY KEY AUTOINCREMENT, item_code TEXT, item_name TEXT, category TEXT, quantity INTEGER, unit_price INTEGER, created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS erp_transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, trans_type TEXT, amount INTEGER, category TEXT, note TEXT, created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS erp_employees (id INTEGER PRIMARY KEY AUTOINCREMENT, full_name TEXT, phone TEXT, position TEXT, department TEXT, base_salary INTEGER, status TEXT DEFAULT 'Đang làm việc', created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS erp_attendance (id INTEGER PRIMARY KEY AUTOINCREMENT, emp_name TEXT, work_date TEXT, time_in TEXT, status TEXT, created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS erp_sales (id INTEGER PRIMARY KEY AUTOINCREMENT, order_code TEXT, customer TEXT, total_amount INTEGER, status TEXT, created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS erp_assets (id INTEGER PRIMARY KEY AUTOINCREMENT, asset_code TEXT, asset_name TEXT, assigned_to TEXT, condition TEXT, status TEXT, created_at TEXT)''')
        
        # BẢNG MỚI: MXH Nội Bộ & OKRs
        c.execute('''CREATE TABLE IF NOT EXISTS erp_social (id INTEGER PRIMARY KEY AUTOINCREMENT, author TEXT, content TEXT, likes INTEGER DEFAULT 0, created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS erp_okrs (id INTEGER PRIMARY KEY AUTOINCREMENT, objective TEXT, key_result TEXT, progress INTEGER DEFAULT 0, owner TEXT, created_at TEXT)''')
        
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
    conn = db_connect(); c = conn.cursor()
    try:
        c.execute("SELECT COUNT(*) FROM erp_customers"); total_customers = c.fetchone()[0] or 0
        c.execute("SELECT COUNT(*), SUM(budget) FROM erp_projects"); proj_data = c.fetchone()
        return {"success": True, "data": {"total_users": total_customers, "total_revenue": proj_data[1] or 0, "total_projects": proj_data[0] or 0}}
    finally: conn.close()

# --- 3. CÁC API CŨ (Giữ nguyên 100%) ---
class CustomerReq(BaseModel): name: str; phone: str; type: str
@router.post("/customers")
async def add_customer(data: CustomerReq):
    conn = db_connect(); c = conn.cursor()
    c.execute("INSERT INTO erp_customers (name, phone, type, created_at) VALUES (?, ?, ?, ?)", (data.name, data.phone, data.type, now_text()))
    conn.commit(); conn.close(); return {"success": True}
@router.get("/customers")
async def get_customers():
    conn = db_connect(); c = conn.cursor(); c.execute("SELECT id, name, phone, type, created_at FROM erp_customers ORDER BY id DESC")
    data = [{"id": r[0], "name": r[1], "phone": r[2], "type": r[3], "created_at": r[4]} for r in c.fetchall()]; conn.close(); return {"success": True, "data": data}

class ProjectReq(BaseModel): project_name: str; customer_name: str; budget: int; status: str
@router.post("/projects")
async def add_project(data: ProjectReq):
    conn = db_connect(); c = conn.cursor()
    c.execute("INSERT INTO erp_projects (project_name, customer_name, budget, status, created_at) VALUES (?, ?, ?, ?, ?)", (data.project_name, data.customer_name, data.budget, data.status, now_text()))
    conn.commit(); conn.close(); return {"success": True}
@router.get("/projects")
async def get_projects():
    conn = db_connect(); c = conn.cursor(); c.execute("SELECT id, project_name, customer_name, budget, status, created_at FROM erp_projects ORDER BY id DESC")
    data = [{"id": r[0], "project_name": r[1], "customer_name": r[2], "budget": r[3], "status": r[4], "created_at": r[5]} for r in c.fetchall()]; conn.close(); return {"success": True, "data": data}

class InventoryReq(BaseModel): item_code: str; item_name: str; category: str; quantity: int; unit_price: int
@router.post("/inventory")
async def add_inventory(data: InventoryReq):
    conn = db_connect(); c = conn.cursor()
    c.execute("INSERT INTO erp_inventory (item_code, item_name, category, quantity, unit_price, created_at) VALUES (?, ?, ?, ?, ?, ?)", (data.item_code, data.item_name, data.category, data.quantity, data.unit_price, now_text()))
    conn.commit(); conn.close(); return {"success": True}
@router.get("/inventory")
async def get_inventory():
    conn = db_connect(); c = conn.cursor(); c.execute("SELECT id, item_code, item_name, category, quantity, unit_price FROM erp_inventory ORDER BY id DESC")
    data = [{"id": r[0], "item_code": r[1], "item_name": r[2], "category": r[3], "quantity": r[4], "unit_price": r[5]} for r in c.fetchall()]; conn.close(); return {"success": True, "data": data}

class FinanceReq(BaseModel): trans_type: str; amount: int; category: str; note: str
@router.post("/finance")
async def add_finance(data: FinanceReq):
    conn = db_connect(); c = conn.cursor()
    c.execute("INSERT INTO erp_transactions (trans_type, amount, category, note, created_at) VALUES (?, ?, ?, ?, ?)", (data.trans_type, data.amount, data.category, data.note, now_text()))
    conn.commit(); conn.close(); return {"success": True}
@router.get("/finance")
async def get_finance():
    conn = db_connect(); c = conn.cursor(); c.execute("SELECT id, trans_type, amount, category, note, created_at FROM erp_transactions ORDER BY id DESC")
    data = [{"id": r[0], "trans_type": r[1], "amount": r[2], "category": r[3], "note": r[4], "created_at": r[5]} for r in c.fetchall()]; conn.close(); return {"success": True, "data": data}

class EmployeeReq(BaseModel): full_name: str; phone: str; position: str; department: str; base_salary: int
@router.post("/employees")
async def add_employee(data: EmployeeReq):
    conn = db_connect(); c = conn.cursor()
    c.execute("INSERT INTO erp_employees (full_name, phone, position, department, base_salary, created_at) VALUES (?, ?, ?, ?, ?, ?)", (data.full_name, data.phone, data.position, data.department, data.base_salary, now_text()))
    conn.commit(); conn.close(); return {"success": True}
@router.get("/employees")
async def get_employees():
    conn = db_connect(); c = conn.cursor(); c.execute("SELECT id, full_name, phone, position, department, base_salary, status FROM erp_employees ORDER BY id DESC")
    data = [{"id": r[0], "full_name": r[1], "phone": r[2], "position": r[3], "department": r[4], "base_salary": r[5], "status": r[6]} for r in c.fetchall()]; conn.close(); return {"success": True, "data": data}

class AttendanceReq(BaseModel): emp_name: str; status: str
@router.post("/attendance")
async def mark_attendance(data: AttendanceReq):
    conn = db_connect(); c = conn.cursor(); date_str = now_text()[:10]; time_str = now_text()[11:16]
    c.execute("INSERT INTO erp_attendance (emp_name, work_date, time_in, status, created_at) VALUES (?, ?, ?, ?, ?)", (data.emp_name, date_str, time_str, data.status, now_text()))
    conn.commit(); conn.close(); return {"success": True}
@router.get("/attendance")
async def get_attendance():
    conn = db_connect(); c = conn.cursor(); c.execute("SELECT id, emp_name, work_date, time_in, status FROM erp_attendance ORDER BY id DESC LIMIT 50")
    data = [{"id": r[0], "emp_name": r[1], "work_date": r[2], "time_in": r[3], "status": r[4]} for r in c.fetchall()]; conn.close(); return {"success": True, "data": data}

class SaleReq(BaseModel): customer: str; total_amount: int; status: str
@router.post("/sales")
async def add_sale(data: SaleReq):
    conn = db_connect(); c = conn.cursor(); order_code = f"DH-{random.randint(1000, 9999)}"
    c.execute("INSERT INTO erp_sales (order_code, customer, total_amount, status, created_at) VALUES (?, ?, ?, ?, ?)", (order_code, data.customer, data.total_amount, data.status, now_text()))
    conn.commit(); conn.close(); return {"success": True}
@router.get("/sales")
async def get_sales():
    conn = db_connect(); c = conn.cursor(); c.execute("SELECT id, order_code, customer, total_amount, status, created_at FROM erp_sales ORDER BY id DESC")
    data = [{"id": r[0], "order_code": r[1], "customer": r[2], "total_amount": r[3], "status": r[4], "created_at": r[5]} for r in c.fetchall()]; conn.close(); return {"success": True, "data": data}

class AssetReq(BaseModel): asset_code: str; asset_name: str; assigned_to: str; condition: str; status: str
@router.post("/assets")
async def add_asset(data: AssetReq):
    conn = db_connect(); c = conn.cursor()
    c.execute("INSERT INTO erp_assets (asset_code, asset_name, assigned_to, condition, status, created_at) VALUES (?, ?, ?, ?, ?, ?)", (data.asset_code, data.asset_name, data.assigned_to, data.condition, data.status, now_text()))
    conn.commit(); conn.close(); return {"success": True}
@router.get("/assets")
async def get_assets():
    conn = db_connect(); c = conn.cursor(); c.execute("SELECT id, asset_code, asset_name, assigned_to, condition, status, created_at FROM erp_assets ORDER BY id DESC")
    data = [{"id": r[0], "asset_code": r[1], "asset_name": r[2], "assigned_to": r[3], "condition": r[4], "status": r[5], "created_at": r[6]} for r in c.fetchall()]; conn.close(); return {"success": True, "data": data}

# --- 4. API MXH NỘI BỘ & OKRs (MỚI) ---
class SocialReq(BaseModel): author: str; content: str
@router.post("/social")
async def add_post(data: SocialReq):
    conn = db_connect(); c = conn.cursor()
    c.execute("INSERT INTO erp_social (author, content, created_at) VALUES (?, ?, ?)", (data.author, data.content, now_text()))
    conn.commit(); conn.close(); return {"success": True}
@router.get("/social")
async def get_posts():
    conn = db_connect(); c = conn.cursor()
    c.execute("SELECT id, author, content, likes, created_at FROM erp_social ORDER BY id DESC")
    data = [{"id": r[0], "author": r[1], "content": r[2], "likes": r[3], "created_at": r[4]} for r in c.fetchall()]
    conn.close(); return {"success": True, "data": data}

class OkrReq(BaseModel): objective: str; key_result: str; progress: int; owner: str
@router.post("/okrs")
async def add_okr(data: OkrReq):
    conn = db_connect(); c = conn.cursor()
    c.execute("INSERT INTO erp_okrs (objective, key_result, progress, owner, created_at) VALUES (?, ?, ?, ?, ?)", (data.objective, data.key_result, data.progress, data.owner, now_text()))
    conn.commit(); conn.close(); return {"success": True}
@router.get("/okrs")
async def get_okrs():
    conn = db_connect(); c = conn.cursor()
    c.execute("SELECT id, objective, key_result, progress, owner FROM erp_okrs ORDER BY id DESC")
    data = [{"id": r[0], "objective": r[1], "key_result": r[2], "progress": r[3], "owner": r[4]} for r in c.fetchall()]
    conn.close(); return {"success": True, "data": data}