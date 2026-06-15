from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging
from db import db_connect, now_text

router = APIRouter()
logger = logging.getLogger("TOAN_AAS_ERP")

# --- AUTO-BUILDER (Khởi tạo Database ERP) ---
def init_erp_database():
    conn = db_connect()
    c = conn.cursor()
    try:
        c.execute("BEGIN IMMEDIATE")
        c.execute('''CREATE TABLE IF NOT EXISTS erp_customers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, email TEXT, type TEXT DEFAULT 'Tiềm năng', source TEXT, created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS erp_projects (id INTEGER PRIMARY KEY AUTOINCREMENT, project_name TEXT, customer_name TEXT, budget INTEGER, status TEXT DEFAULT 'Đang triển khai', created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS erp_transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT, amount INTEGER, category TEXT, note TEXT, created_at TEXT)''')
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Lỗi khởi tạo ERP: {e}")
    finally:
        conn.close()

init_erp_database()

# --- API THỐNG KÊ TỔNG QUAN ---
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
        
        return {
            "success": True, 
            "data": {
                "total_users": total_customers,
                "total_revenue": total_revenue,
                "total_projects": total_projects,
                "active_tools": 8
            }
        }
    finally:
        conn.close()

# --- API QUẢN LÝ KHÁCH HÀNG (CRM) ---
class CustomerReq(BaseModel):
    name: str
    phone: str
    type: str

@router.post("/customers")
async def add_customer(data: CustomerReq):
    conn = db_connect()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO erp_customers (name, phone, type, created_at) VALUES (?, ?, ?, ?)", 
                  (data.name, data.phone, data.type, now_text()))
        conn.commit()
        return {"success": True, "message": "Đã thêm Khách hàng mới!"}
    finally:
        conn.close()

@router.get("/customers")
async def get_customers():
    conn = db_connect()
    c = conn.cursor()
    try:
        c.execute("SELECT id, name, phone, type, created_at FROM erp_customers ORDER BY id DESC")
        data = [{"id": r[0], "name": r[1], "phone": r[2], "type": r[3], "created_at": r[4]} for r in c.fetchall()]
        return {"success": True, "data": data}
    finally:
        conn.close()

# --- API QUẢN LÝ DỰ ÁN (B2B ELV) ---
class ProjectReq(BaseModel):
    project_name: str
    customer_name: str
    budget: int
    status: str

@router.post("/projects")
async def add_project(data: ProjectReq):
    conn = db_connect()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO erp_projects (project_name, customer_name, budget, status, created_at) VALUES (?, ?, ?, ?, ?)", 
                  (data.project_name, data.customer_name, data.budget, data.status, now_text()))
        conn.commit()
        return {"success": True, "message": "Đã tạo Dự án mới!"}
    finally:
        conn.close()

@router.get("/projects")
async def get_projects():
    conn = db_connect()
    c = conn.cursor()
    try:
        c.execute("SELECT id, project_name, customer_name, budget, status, created_at FROM erp_projects ORDER BY id DESC")
        data = [{"id": r[0], "project_name": r[1], "customer_name": r[2], "budget": r[3], "status": r[4], "created_at": r[5]} for r in c.fetchall()]
        return {"success": True, "data": data}
    finally:
        conn.close()