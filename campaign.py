from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging
from db import db_connect, now_text

router = APIRouter()
logger = logging.getLogger("TOAN_AAS_CAMPAIGN")

class CampaignCreate(BaseModel):
    user_id: str
    campaign_name: str
    product_link: str
    platform: str

@router.post("/create")
async def create_campaign(request: CampaignCreate):
    conn = db_connect()
    c = conn.cursor()
    try:
        # Tự động tạo bảng nếu chưa tồn tại
        c.execute("""CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            campaign_name TEXT,
            product_link TEXT,
            platform TEXT,
            created_at DATETIME
        )""")
        
        c.execute(
            "INSERT INTO campaigns (user_id, campaign_name, product_link, platform, created_at) VALUES (?, ?, ?, ?, ?)",
            (request.user_id, request.campaign_name, request.product_link, request.platform, now_text())
        )
        conn.commit()
        return {"success": True, "message": "Đã tạo chiến dịch B2C thành công!"}
    except Exception as e:
        logger.error(f"Lỗi tạo campaign: {e}")
        raise HTTPException(status_code=500, detail="Không tạo được chiến dịch")
    finally:
        conn.close()

@router.get("/{user_id}")
async def get_campaigns(user_id: str):
    conn = db_connect()
    c = conn.cursor()
    try:
        # Kiểm tra xem bảng đã được tạo chưa để tránh lỗi
        c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='campaigns'")
        if not c.fetchone():
            return {"success": True, "data": []}
            
        c.execute("SELECT id, campaign_name, product_link, platform, created_at FROM campaigns WHERE user_id=?", (user_id,))
        rows = [{"id": r[0], "name": r[1], "link": r[2], "platform": r[3], "date": r[4]} for r in c.fetchall()]
        return {"success": True, "data": rows}
    finally:
        conn.close()