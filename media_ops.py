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
            user_id TEXT,
            title TEXT,
            media_type TEXT,
            content TEXT,
            created_at TEXT
        )
    ''')
    c.execute("PRAGMA table_info(media_assets)")
    existing = {row[1] for row in c.fetchall()}
    if "user_id" not in existing:
        c.execute("ALTER TABLE media_assets ADD COLUMN user_id TEXT")
    conn.commit()
    conn.close()

init_media_db()

class MediaCreate(BaseModel):
    user_id: str = ""
    title: str
    media_type: str
    content: str

@router.post("/assets")
async def save_asset(data: MediaCreate):
    try:
        conn = db_connect()
        c = conn.cursor()
        c.execute(
            "INSERT INTO media_assets (user_id, title, media_type, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (data.user_id, data.title, data.media_type, data.content, now_text())
        )
        conn.commit()
        conn.close()
        return {"success": True, "message": "Lưu tài nguyên thành công"}
    except Exception as e:
        logger.error(f"Lỗi lưu Media: {e}")
        raise HTTPException(status_code=500, detail="Lỗi máy chủ")

@router.get("/assets")
async def get_assets(user_id: str = ""):
    try:
        conn = db_connect()
        c = conn.cursor()
        if user_id:
            c.execute("SELECT id, title, media_type, content, created_at FROM media_assets WHERE user_id=? OR user_id IS NULL OR user_id='' ORDER BY id DESC", (user_id,))
        else:
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
