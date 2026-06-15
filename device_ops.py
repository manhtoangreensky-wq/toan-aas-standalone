from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging
from db import db_connect, now_text

router = APIRouter()
logger = logging.getLogger("TOAN_AAS_B2B")

# Khởi tạo bảng dữ liệu cho dự án B2B
def init_b2b_db():
    conn = db_connect()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS b2b_projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            client TEXT,
            category TEXT,
            status TEXT DEFAULT 'Đang triển khai',
            budget INTEGER DEFAULT 0,
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_b2b_db()

class ProjectCreate(BaseModel):
    name: str
    client: str
    category: str
    budget: int

@router.post("/projects")
async def create_project(data: ProjectCreate):
    try:
        conn = db_connect()
        c = conn.cursor()
        c.execute(
            "INSERT INTO b2b_projects (name, client, category, budget, created_at) VALUES (?, ?, ?, ?, ?)",
            (data.name, data.client, data.category, data.budget, now_text())
        )
        conn.commit()
        conn.close()
        return {"success": True, "message": "Tạo dự án thành công"}
    except Exception as e:
        logger.error(f"Lỗi tạo dự án B2B: {e}")
        raise HTTPException(status_code=500, detail="Lỗi máy chủ")

@router.get("/projects")
async def get_projects():
    try:
        conn = db_connect()
        c = conn.cursor()
        c.execute("SELECT id, name, client, category, status, budget, created_at FROM b2b_projects ORDER BY id DESC")
        rows = c.fetchall()
        conn.close()
        
        projects = []
        for r in rows:
            projects.append({
                "id": r[0], "name": r[1], "client": r[2], 
                "category": r[3], "status": r[4], 
                "budget": r[5], "created_at": r[6]
            })
        return {"success": True, "data": projects}
    except Exception as e:
        logger.error(f"Lỗi tải dự án B2B: {e}")
        return {"success": False, "data": []}