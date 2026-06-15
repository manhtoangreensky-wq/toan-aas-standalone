from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging
from db import db_connect, now_text

router = APIRouter()
logger = logging.getLogger("TOAN_AAS_CAMPAIGN")

# Tự động tạo bảng lưu trữ chiến dịch B2C
def init_db():
    conn = db_connect()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS campaigns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        name TEXT,
        link TEXT,
        platform TEXT,
        created_at TEXT
    )''')
    conn.commit()
    conn.close()

init_db()

class CampaignCreate(BaseModel):
    user_id: str
    campaign_name: str
    product_link: str
    platform: str

@router.post("/create")
async def create_campaign(data: CampaignCreate):
    try:
        conn = db_connect()
        c = conn.cursor()
        c.execute("INSERT INTO campaigns (user_id, name, link, platform, created_at) VALUES (?, ?, ?, ?, ?)",
                  (data.user_id, data.campaign_name, data.product_link, data.platform, now_text()))
        conn.commit()
        return {"success": True}
    except Exception as e:
        logger.error(f"Lỗi tạo chiến dịch: {e}")
        return {"success": False, "message": "Lỗi server"}
    finally:
        conn.close()

@router.get("/{user_id}")
async def get_campaigns(user_id: str):
    try:
        conn = db_connect()
        c = conn.cursor()
        c.execute("SELECT name, link, platform, created_at FROM campaigns WHERE user_id=? ORDER BY id DESC", (user_id,))
        rows = c.fetchall()
        data = [{"name": r[0], "link": r[1], "platform": r[2], "date": r[3]} for r in rows]
        return {"success": True, "data": data}
    except Exception as e:
        logger.error(f"Lỗi lấy chiến dịch: {e}")
        return {"success": False, "data": []}
    finally:
        conn.close()