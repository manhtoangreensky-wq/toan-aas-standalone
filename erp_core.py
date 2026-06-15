from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging
from db import db_connect, now_text
import random

router = APIRouter()
logger = logging.getLogger("TOAN_AAS_ERP")

def init_erp_database():
    conn = db_connect(); c = conn.cursor()
    try:
        c.execute("BEGIN IMMEDIATE")
        # 12 Bảng cũ
        c.execute('''CREATE TABLE IF NOT EXISTS erp_customers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, email TEXT, type TEXT DEFAULT 'Tiềm năng', source TEXT, created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS erp_projects (id INTEGER PRIMARY KEY AUTOINCREMENT, project_name TEXT, customer_name TEXT, budget INTEGER, status TEXT DEFAULT 'Đang triển khai', created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS erp_inventory (id INTEGER PRIMARY KEY AUTOINCREMENT, item_code TEXT, item_name TEXT, category TEXT, quantity INTEGER, unit_price INTEGER, created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS erp_transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, trans_type TEXT, amount INTEGER, category TEXT, note TEXT, created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS erp_employees (id INTEGER PRIMARY KEY AUTOINCREMENT, full_name TEXT, phone TEXT, position TEXT, department TEXT, base_salary INTEGER, status TEXT DEFAULT 'Đang làm việc', created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS erp_attendance (id INTEGER PRIMARY KEY AUTOINCREMENT, emp_name TEXT, work_date TEXT, time_in TEXT, status TEXT, created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS erp_sales (id INTEGER PRIMARY KEY AUTOINCREMENT, order_code TEXT, customer TEXT, total_amount INTEGER, status TEXT, created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS erp_assets (id INTEGER PRIMARY KEY AUTOINCREMENT, asset_code TEXT, asset_name TEXT, assigned_to TEXT, condition TEXT, status TEXT, created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS erp_social (id INTEGER PRIMARY KEY AUTOINCREMENT, author TEXT, content TEXT, likes INTEGER DEFAULT 0, created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS erp_okrs (id INTEGER PRIMARY KEY AUTOINCREMENT, objective TEXT, key_result TEXT, progress INTEGER DEFAULT 0, owner TEXT, created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS erp_purchases (id INTEGER PRIMARY KEY AUTOINCREMENT, po_code TEXT, supplier TEXT, total_amount INTEGER, status TEXT, created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS erp_approvals (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, req_type TEXT, requested_by TEXT, status TEXT DEFAULT 'Chờ duyệt', created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS erp_production (id INTEGER PRIMARY KEY AUTOINCREMENT, batch_code TEXT, product_name TEXT, quantity INTEGER, status TEXT, created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS erp_workloads (id INTEGER PRIMARY KEY AUTOINCREMENT, task_name TEXT, emp_name TEXT, est_hours INTEGER, status TEXT, created_at TEXT)''')
        
        # BẢNG MỚI: MỤC TIÊU & BANNER PR
        c.execute('''CREATE TABLE IF NOT EXISTS erp_goals (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, target_value INTEGER, current_value INTEGER DEFAULT 0, deadline TEXT, created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS erp_banners (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, image_url TEXT, status TEXT DEFAULT 'Hoạt động', created_at TEXT)''')
        
        conn.commit()
    except Exception as e:
        conn.rollback(); logger.error(f"Lỗi: {e}")
    finally: conn.close()

init_erp_database()

@router.get("/dashboard-stats")
async def get_erp_stats():
    conn = db_connect(); c = conn.cursor()
    try:
        c.execute("SELECT COUNT(*) FROM erp_customers"); total_customers = c.fetchone()[0] or 0
        c.execute("SELECT COUNT(*), SUM(budget) FROM erp_projects"); proj_data = c.fetchone()
        return {"success": True, "data": {"total_users": total_customers, "total_revenue": proj_data[1] or 0, "total_projects": proj_data[0] or 0}}
    finally: conn.close()

# --- CÁC API CŨ (Đã rút gọn) ---
class CustomerReq(BaseModel): name: str; phone: str; type: str
@router.post("/customers")
async def add_customer(data: CustomerReq): conn = db_connect(); c = conn.cursor(); c.execute("INSERT INTO erp_customers (name, phone, type, created_at) VALUES (?, ?, ?, ?)", (data.name, data.phone, data.type, now_text())); conn.commit(); conn.close(); return {"success": True}
@router.get("/customers")
async def get_customers(): conn = db_connect(); c = conn.cursor(); c.execute("SELECT id, name, phone, type, created_at FROM erp_customers ORDER BY id DESC"); data = [{"id": r[0], "name": r[1], "phone": r[2], "type": r[3], "created_at": r[4]} for r in c.fetchall()]; conn.close(); return {"success": True, "data": data}

class ProjectReq(BaseModel): project_name: str; customer_name: str; budget: int; status: str
@router.post("/projects")
async def add_project(data: ProjectReq): conn = db_connect(); c = conn.cursor(); c.execute("INSERT INTO erp_projects (project_name, customer_name, budget, status, created_at) VALUES (?, ?, ?, ?, ?)", (data.project_name, data.customer_name, data.budget, data.status, now_text())); conn.commit(); conn.close(); return {"success": True}
@router.get("/projects")
async def get_projects(): conn = db_connect(); c = conn.cursor(); c.execute("SELECT id, project_name, customer_name, budget, status, created_at FROM erp_projects ORDER BY id DESC"); data = [{"id": r[0], "project_name": r[1], "customer_name": r[2], "budget": r[3], "status": r[4], "created_at": r[5]} for r in c.fetchall()]; conn.close(); return {"success": True, "data": data}

class InventoryReq(BaseModel): item_code: str; item_name: str; category: str; quantity: int; unit_price: int
@router.post("/inventory")
async def add_inventory(data: InventoryReq): conn = db_connect(); c = conn.cursor(); c.execute("INSERT INTO erp_inventory (item_code, item_name, category, quantity, unit_price, created_at) VALUES (?, ?, ?, ?, ?, ?)", (data.item_code, data.item_name, data.category, data.quantity, data.unit_price, now_text())); conn.commit(); conn.close(); return {"success": True}
@router.get("/inventory")
async def get_inventory(): conn = db_connect(); c = conn.cursor(); c.execute("SELECT id, item_code, item_name, category, quantity, unit_price FROM erp_inventory ORDER BY id DESC"); data = [{"id": r[0], "item_code": r[1], "item_name": r[2], "category": r[3], "quantity": r[4], "unit_price": r[5]} for r in c.fetchall()]; conn.close(); return {"success": True, "data": data}

class FinanceReq(BaseModel): trans_type: str; amount: int; category: str; note: str
@router.post("/finance")
async def add_finance(data: FinanceReq): conn = db_connect(); c = conn.cursor(); c.execute("INSERT INTO erp_transactions (trans_type, amount, category, note, created_at) VALUES (?, ?, ?, ?, ?)", (data.trans_type, data.amount, data.category, data.note, now_text())); conn.commit(); conn.close(); return {"success": True}
@router.get("/finance")
async def get_finance(): conn = db_connect(); c = conn.cursor(); c.execute("SELECT id, trans_type, amount, category, note, created_at FROM erp_transactions ORDER BY id DESC"); data = [{"id": r[0], "trans_type": r[1], "amount": r[2], "category": r[3], "note": r[4], "created_at": r[5]} for r in c.fetchall()]; conn.close(); return {"success": True, "data": data}

class EmployeeReq(BaseModel): full_name: str; phone: str; position: str; department: str; base_salary: int
@router.post("/employees")
async def add_employee(data: EmployeeReq): conn = db_connect(); c = conn.cursor(); c.execute("INSERT INTO erp_employees (full_name, phone, position, department, base_salary, created_at) VALUES (?, ?, ?, ?, ?, ?)", (data.full_name, data.phone, data.position, data.department, data.base_salary, now_text())); conn.commit(); conn.close(); return {"success": True}
@router.get("/employees")
async def get_employees(): conn = db_connect(); c = conn.cursor(); c.execute("SELECT id, full_name, phone, position, department, base_salary, status FROM erp_employees ORDER BY id DESC"); data = [{"id": r[0], "full_name": r[1], "phone": r[2], "position": r[3], "department": r[4], "base_salary": r[5], "status": r[6]} for r in c.fetchall()]; conn.close(); return {"success": True, "data": data}

class AttendanceReq(BaseModel): emp_name: str; status: str
@router.post("/attendance")
async def mark_attendance(data: AttendanceReq): conn = db_connect(); c = conn.cursor(); c.execute("INSERT INTO erp_attendance (emp_name, work_date, time_in, status, created_at) VALUES (?, ?, ?, ?, ?)", (data.emp_name, now_text()[:10], now_text()[11:16], data.status, now_text())); conn.commit(); conn.close(); return {"success": True}
@router.get("/attendance")
async def get_attendance(): conn = db_connect(); c = conn.cursor(); c.execute("SELECT id, emp_name, work_date, time_in, status FROM erp_attendance ORDER BY id DESC LIMIT 50"); data = [{"id": r[0], "emp_name": r[1], "work_date": r[2], "time_in": r[3], "status": r[4]} for r in c.fetchall()]; conn.close(); return {"success": True, "data": data}

class SaleReq(BaseModel): customer: str; total_amount: int; status: str
@router.post("/sales")
async def add_sale(data: SaleReq): conn = db_connect(); c = conn.cursor(); c.execute("INSERT INTO erp_sales (order_code, customer, total_amount, status, created_at) VALUES (?, ?, ?, ?, ?)", (f"DH-{random.randint(1000, 9999)}", data.customer, data.total_amount, data.status, now_text())); conn.commit(); conn.close(); return {"success": True}
@router.get("/sales")
async def get_sales(): conn = db_connect(); c = conn.cursor(); c.execute("SELECT id, order_code, customer, total_amount, status, created_at FROM erp_sales ORDER BY id DESC"); data = [{"id": r[0], "order_code": r[1], "customer": r[2], "total_amount": r[3], "status": r[4], "created_at": r[5]} for r in c.fetchall()]; conn.close(); return {"success": True, "data": data}

class AssetReq(BaseModel): asset_code: str; asset_name: str; assigned_to: str; condition: str; status: str
@router.post("/assets")
async def add_asset(data: AssetReq): conn = db_connect(); c = conn.cursor(); c.execute("INSERT INTO erp_assets (asset_code, asset_name, assigned_to, condition, status, created_at) VALUES (?, ?, ?, ?, ?, ?)", (data.asset_code, data.asset_name, data.assigned_to, data.condition, data.status, now_text())); conn.commit(); conn.close(); return {"success": True}
@router.get("/assets")
async def get_assets(): conn = db_connect(); c = conn.cursor(); c.execute("SELECT id, asset_code, asset_name, assigned_to, condition, status, created_at FROM erp_assets ORDER BY id DESC"); data = [{"id": r[0], "asset_code": r[1], "asset_name": r[2], "assigned_to": r[3], "condition": r[4], "status": r[5], "created_at": r[6]} for r in c.fetchall()]; conn.close(); return {"success": True, "data": data}

class SocialReq(BaseModel): author: str; content: str
@router.post("/social")
async def add_post(data: SocialReq): conn = db_connect(); c = conn.cursor(); c.execute("INSERT INTO erp_social (author, content, created_at) VALUES (?, ?, ?)", (data.author, data.content, now_text())); conn.commit(); conn.close(); return {"success": True}
@router.get("/social")
async def get_posts(): conn = db_connect(); c = conn.cursor(); c.execute("SELECT id, author, content, likes, created_at FROM erp_social ORDER BY id DESC"); data = [{"id": r[0], "author": r[1], "content": r[2], "likes": r[3], "created_at": r[4]} for r in c.fetchall()]; conn.close(); return {"success": True, "data": data}

class OkrReq(BaseModel): objective: str; key_result: str; progress: int; owner: str
@router.post("/okrs")
async def add_okr(data: OkrReq): conn = db_connect(); c = conn.cursor(); c.execute("INSERT INTO erp_okrs (objective, key_result, progress, owner, created_at) VALUES (?, ?, ?, ?, ?)", (data.objective, data.key_result, data.progress, data.owner, now_text())); conn.commit(); conn.close(); return {"success": True}
@router.get("/okrs")
async def get_okrs(): conn = db_connect(); c = conn.cursor(); c.execute("SELECT id, objective, key_result, progress, owner FROM erp_okrs ORDER BY id DESC"); data = [{"id": r[0], "objective": r[1], "key_result": r[2], "progress": r[3], "owner": r[4]} for r in c.fetchall()]; conn.close(); return {"success": True, "data": data}

class PurchaseReq(BaseModel): supplier: str; total_amount: int; status: str
@router.post("/purchases")
async def add_purchase(data: PurchaseReq): conn = db_connect(); c = conn.cursor(); c.execute("INSERT INTO erp_purchases (po_code, supplier, total_amount, status, created_at) VALUES (?, ?, ?, ?, ?)", (f"PO-{random.randint(100, 999)}", data.supplier, data.total_amount, data.status, now_text())); conn.commit(); conn.close(); return {"success": True}
@router.get("/purchases")
async def get_purchases(): conn = db_connect(); c = conn.cursor(); c.execute("SELECT id, po_code, supplier, total_amount, status, created_at FROM erp_purchases ORDER BY id DESC"); data = [{"id": r[0], "po_code": r[1], "supplier": r[2], "total_amount": r[3], "status": r[4], "created_at": r[5]} for r in c.fetchall()]; conn.close(); return {"success": True, "data": data}

class ApprovalReq(BaseModel): title: str; req_type: str; requested_by: str; status: str
@router.post("/approvals")
async def add_approval(data: ApprovalReq): conn = db_connect(); c = conn.cursor(); c.execute("INSERT INTO erp_approvals (title, req_type, requested_by, status, created_at) VALUES (?, ?, ?, ?, ?)", (data.title, data.req_type, data.requested_by, data.status, now_text())); conn.commit(); conn.close(); return {"success": True}
@router.get("/approvals")
async def get_approvals(): conn = db_connect(); c = conn.cursor(); c.execute("SELECT id, title, req_type, requested_by, status, created_at FROM erp_approvals ORDER BY id DESC"); data = [{"id": r[0], "title": r[1], "req_type": r[2], "requested_by": r[3], "status": r[4], "created_at": r[5]} for r in c.fetchall()]; conn.close(); return {"success": True, "data": data}

class ProductionReq(BaseModel): product_name: str; quantity: int; status: str
@router.post("/production")
async def add_production(data: ProductionReq): conn = db_connect(); c = conn.cursor(); c.execute("INSERT INTO erp_production (batch_code, product_name, quantity, status, created_at) VALUES (?, ?, ?, ?, ?)", (f"SX-{random.randint(1000, 9999)}", data.product_name, data.quantity, data.status, now_text())); conn.commit(); conn.close(); return {"success": True}
@router.get("/production")
async def get_production(): conn = db_connect(); c = conn.cursor(); c.execute("SELECT id, batch_code, product_name, quantity, status, created_at FROM erp_production ORDER BY id DESC"); data = [{"id": r[0], "batch_code": r[1], "product_name": r[2], "quantity": r[3], "status": r[4], "created_at": r[5]} for r in c.fetchall()]; conn.close(); return {"success": True, "data": data}

class WorkloadReq(BaseModel): task_name: str; emp_name: str; est_hours: int; status: str
@router.post("/workloads")
async def add_workload(data: WorkloadReq): conn = db_connect(); c = conn.cursor(); c.execute("INSERT INTO erp_workloads (task_name, emp_name, est_hours, status, created_at) VALUES (?, ?, ?, ?, ?)", (data.task_name, data.emp_name, data.est_hours, data.status, now_text())); conn.commit(); conn.close(); return {"success": True}
@router.get("/workloads")
async def get_workloads(): conn = db_connect(); c = conn.cursor(); c.execute("SELECT id, task_name, emp_name, est_hours, status, created_at FROM erp_workloads ORDER BY id DESC"); data = [{"id": r[0], "task_name": r[1], "emp_name": r[2], "est_hours": r[3], "status": r[4], "created_at": r[5]} for r in c.fetchall()]; conn.close(); return {"success": True, "data": data}

# --- 6. API MỤC TIÊU KINH DOANH & BANNER PR (MỚI) ---
class GoalReq(BaseModel): title: str; target_value: int; deadline: str
@router.post("/goals")
async def add_goal(data: GoalReq):
    conn = db_connect(); c = conn.cursor()
    c.execute("INSERT INTO erp_goals (title, target_value, deadline, created_at) VALUES (?, ?, ?, ?)", 
              (data.title, data.target_value, data.deadline, now_text()))
    conn.commit(); conn.close(); return {"success": True}

@router.get("/goals")
async def get_goals():
    conn = db_connect(); c = conn.cursor()
    c.execute("SELECT id, title, target_value, current_value, deadline FROM erp_goals ORDER BY id DESC")
    data = [{"id": r[0], "title": r[1], "target_value": r[2], "current_value": r[3], "deadline": r[4]} for r in c.fetchall()]
    conn.close(); return {"success": True, "data": data}

class BannerReq(BaseModel): title: str; image_url: str; status: str
@router.post("/banners")
async def add_banner(data: BannerReq):
    conn = db_connect(); c = conn.cursor()
    c.execute("INSERT INTO erp_banners (title, image_url, status, created_at) VALUES (?, ?, ?, ?)", 
              (data.title, data.image_url, data.status, now_text()))
    conn.commit(); conn.close(); return {"success": True}

@router.get("/banners")
async def get_banners():
    conn = db_connect(); c = conn.cursor()
    c.execute("SELECT id, title, image_url, status, created_at FROM erp_banners ORDER BY id DESC")
    data = [{"id": r[0], "title": r[1], "image_url": r[2], "status": r[3], "created_at": r[4]} for r in c.fetchall()]
    conn.close(); return {"success": True, "data": data}