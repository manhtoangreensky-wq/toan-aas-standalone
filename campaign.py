from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging
from db import db_connect, now_text

router = APIRouter()
logger = logging.getLogger("TOAN_AAS_CAMPAIGN")

# --- Model đầu vào ---
class CampaignCreate(BaseModel):
    user_id: str
    campaign_name: str
    product_link: str
    platform: str

# --- API 1: Tạo chiến dịch Affiliate mới ---
@router.post("/create")
async def create_campaign(request: CampaignCreate):
    conn = db_connect()
    c = conn.cursor()
    try:
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

# --- API 2: Liệt kê chiến dịch của khách ---
@router.get("/{user_id}")
async def get_campaigns(user_id: str):
    conn = db_connect()
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM campaigns WHERE user_id=?", (user_id,))
        rows = c.fetchall()
        return {"success": True, "data": rows}
    finally:
        conn.close()