from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging
from db import db_connect, now_text

router = APIRouter()
logger = logging.getLogger("TOAN_AAS_MEDIA")

# Khởi tạo bảng lưu trữ tài sản Media AI
def init_media_db():
    conn = db_connect()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS media_assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            media_type TEXT,
            content TEXT,
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_media_db()

class MediaCreate(BaseModel):
    title: str
    media_type: str
    content: str

@router.post("/assets")
async def save_asset(data: MediaCreate):
    try:
        conn = db_connect()
        c = conn.cursor()
        c.execute(
            "INSERT INTO media_assets (title, media_type, content, created_at) VALUES (?, ?, ?, ?)",
            (data.title, data.media_type, data.content, now_text())
        )
        conn.commit()
        conn.close()
        return {"success": True, "message": "Lưu tài nguyên thành công"}
    except Exception as e:
        logger.error(f"Lỗi lưu Media: {e}")
        raise HTTPException(status_code=500, detail="Lỗi máy chủ")

@router.get("/assets")
async def get_assets():
    try:
        conn = db_connect()
        c = conn.cursor()
        c.execute("SELECT id, title, media_type, content, created_at FROM media_assets ORDER BY id DESC")
        rows = c.fetchall()
        conn.close()
        
        assets = []
        for r in rows:
            assets.append({
                "id": r[0], "title": r[1], "media_type": r[2], 
                "content": r[3], "created_at": r[4]
            })
        return {"success": True, "data": assets}
    except Exception as e:
        logger.error(f"Lỗi tải Media: {e}")
        return {"success": False, "data": []}