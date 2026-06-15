from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging
from db import db_connect, now_text

router = APIRouter()
logger = logging.getLogger("TOAN_AAS_DEVICE_OPS")

# --- Các mô hình dữ liệu ---
class ProjectCreate(BaseModel):
    user_id: str
    customer_name: str
    project_type: str  # Ví dụ: 'Hệ thống ELV', 'Camera An Ninh', 'Âm thanh Ánh sáng'
    budget: int = 0
    note: str = ""

class TaskAdd(BaseModel):
    project_id: int
    device_name: str
    task_detail: str

# --- API 1: Khởi tạo dự án thi công/bảo trì ---
@router.post("/projects")
async def create_project(data: ProjectCreate):
    conn = db_connect()
    c = conn.cursor()
    try:
        # Tự động tạo bảng Quản lý Dự án
        c.execute("""CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            customer_name TEXT,
            project_type TEXT,
            budget INTEGER,
            status TEXT DEFAULT 'Khảo sát',
            note TEXT,
            created_at DATETIME
        )""")
        
        c.execute(
            "INSERT INTO projects (user_id, customer_name, project_type, budget, note, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (data.user_id, data.customer_name, data.project_type, data.budget, data.note, now_text())
        )
        conn.commit()
        return {"success": True, "message": f"Đã lên hồ sơ dự án {data.project_type} cho khách hàng {data.customer_name}!"}
    except Exception as e:
        logger.error(f"Lỗi tạo dự án B2B: {e}")
        raise HTTPException(status_code=500, detail="Không thể lưu dự án")
    finally:
        conn.close()

# --- API 2: Lên Checklist thi công thiết bị ---
@router.post("/tasks")
async def add_device_task(data: TaskAdd):
    conn = db_connect()
    c = conn.cursor()
    try:
        # Tự động tạo bảng Checklist Thiết bị
        c.execute("""CREATE TABLE IF NOT EXISTS device_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            device_name TEXT,
            task_detail TEXT,
            is_completed INTEGER DEFAULT 0,
            created_at DATETIME
        )""")
        
        c.execute(
            "INSERT INTO device_tasks (project_id, device_name, task_detail, created_at) VALUES (?, ?, ?, ?)",
            (data.project_id, data.device_name, data.task_detail, now_text())
        )
        conn.commit()
        return {"success": True, "message": "Đã thêm thiết bị vào checklist thi công!"}
    except Exception as e:
        logger.error(f"Lỗi thêm task thiết bị: {e}")
        raise HTTPException(status_code=500, detail="Không thể lưu checklist")
    finally:
        conn.close()

# --- API 3: Lấy danh sách dự án ---
@router.get("/projects/{user_id}")
async def get_projects(user_id: str):
    conn = db_connect()
    c = conn.cursor()
    try:
        c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='projects'")
        if not c.fetchone():
            return {"success": True, "data": []}
            
        c.execute("SELECT id, customer_name, project_type, budget, status, created_at FROM projects WHERE user_id=?", (user_id,))
        rows = [{"id": r[0], "customer": r[1], "type": r[2], "budget": r[3], "status": r[4], "date": r[5]} for r in c.fetchall()]
        return {"success": True, "data": rows}
    finally:
        conn.close()