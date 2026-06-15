from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging
import random
from db import db_connect, now_text

router = APIRouter()
logger = logging.getLogger("TOAN_AAS_ERP")

# ==========================================
# 1. AUTO-BUILDER: TỰ ĐỘNG XÂY DỰNG 4 TRỤ CỘT ERP
# ==========================================
def init_erp_database():
    conn = db_connect()
    c = conn.cursor()
    try:
        c.execute("BEGIN IMMEDIATE")
        
        # TRỤ CỘT 1: CRM & BÁN HÀNG
        c.execute('''CREATE TABLE IF NOT EXISTS erp_customers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, email TEXT, type TEXT DEFAULT 'Tiềm năng', source TEXT, created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS erp_deals (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, deal_name TEXT, amount INTEGER, status TEXT DEFAULT 'Đang thương lượng', created_at TEXT)''')
        
        # TRỤ CỘT 2: VẬN HÀNH & KHO BÃI (ELV/Camera)
        c.execute('''CREATE TABLE IF NOT EXISTS erp_inventory (id INTEGER PRIMARY KEY AUTOINCREMENT, item_code TEXT, item_name TEXT, category TEXT, quantity INTEGER, unit_price INTEGER, created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS erp_projects (id INTEGER PRIMARY KEY AUTOINCREMENT, project_name TEXT, customer_name TEXT, budget INTEGER, status TEXT DEFAULT 'Đang triển khai', created_at TEXT)''')
        
        # TRỤ CỘT 3: TÀI CHÍNH KẾ TOÁN
        c.execute('''CREATE TABLE IF NOT EXISTS erp_transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT, amount INTEGER, category TEXT, note TEXT, created_at TEXT)''')
        
        # TRỤ CỘT 4: NHÂN SỰ & NỘI BỘ
        c.execute('''CREATE TABLE IF NOT EXISTS erp_employees (id INTEGER PRIMARY KEY AUTOINCREMENT, full_name TEXT, position TEXT, department TEXT, base_salary INTEGER, join_date TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS erp_attendance (id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id INTEGER, check_in_time TEXT, status TEXT)''')
        
        conn.commit()
        logger.info("Đã xây dựng thành công 4 Trụ Cột ERP!")
    except Exception as e:
        conn.rollback()
        logger.error(f"Lỗi khởi tạo ERP: {e}")
    finally:
        conn.close()

# Kích hoạt xây dựng Database ngay lập tức
init_erp_database()

# ==========================================
# 2. API LẤY CHỈ SỐ CHO BẢNG ĐIỀU KHIỂN
# ==========================================
@router.get("/dashboard-stats")
async def get_erp_stats():
    conn = db_connect()
    c = conn.cursor()
    try:
        # Đếm tổng khách hàng CRM
        c.execute("SELECT COUNT(*) FROM erp_customers")
        total_customers = c.fetchone()[0] or 0
        
        # Đếm doanh thu (Giả lập tính từ Deals thành công + PayOS)
        c.execute("SELECT SUM(amount) FROM erp_deals WHERE status='Thành công'")
        deal_revenue = c.fetchone()[0] or 0
        
        try:
            c.execute("SELECT SUM(amount) FROM payos_orders WHERE status='PAID'")
            payos_revenue = c.fetchone()[0] or 0
        except:
            payos_revenue = 0
            
        total_revenue = deal_revenue + payos_revenue
        
        # Số lượng dự án B2B
        c.execute("SELECT COUNT(*) FROM erp_projects")
        total_projects = c.fetchone()[0] or 0
        
        return {
            "success": True, 
            "data": {
                "total_users": total_customers,
                "total_revenue": total_revenue,
                "total_projects": total_projects,
                "active_tools": 8 # Số công cụ hệ thống hiện có
            }
        }
    except Exception as e:
        return {"success": False, "message": str(e)}
    finally:
        conn.close()

# ==========================================
# 3. API BƠM DỮ LIỆU GIẢ (TEST DATA)
# ==========================================
@router.post("/seed-demo-data")
async def seed_erp_data():
    conn = db_connect()
    c = conn.cursor()
    try:
        c.execute("BEGIN IMMEDIATE")
        
        # Bơm 50 Khách hàng
        for i in range(1, 51):
            c.execute("INSERT INTO erp_customers (name, phone, type, created_at) VALUES (?, ?, ?, ?)", 
                      (f"Khách hàng Doanh nghiệp {i}", f"0901234{i:03d}", random.choice(['Tiềm năng', 'Đã chốt']), now_text()))
            
        # Bơm 15 Dự án ELV & Doanh thu
        for i in range(1, 16):
            budget = random.randint(50, 500) * 1000000 # 50tr - 500tr
            c.execute("INSERT INTO erp_projects (project_name, customer_name, budget, status, created_at) VALUES (?, ?, ?, ?, ?)",
                      (f"Thi công Camera Phân xưởng {i}", f"Công ty TNHH {i}", budget, random.choice(['Hoàn thành', 'Đang triển khai']), now_text()))
            
            c.execute("INSERT INTO erp_deals (customer_id, deal_name, amount, status, created_at) VALUES (?, ?, ?, ?, ?)",
                      (i, f"Hợp đồng cung cấp vật tư {i}", budget, 'Thành công', now_text()))

        conn.commit()
        return {"success": True, "message": "Đã bơm thành công dữ liệu Demo! Hãy F5 lại bảng điều khiển."}
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": str(e)}
    finally:
        conn.close()