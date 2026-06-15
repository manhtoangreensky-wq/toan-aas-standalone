from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging
from db import db_connect, now_text

router = APIRouter()
logger = logging.getLogger("TOAN_AAS_PERFORMANCE")

class PerformanceAdd(BaseModel):
    user_id: str
    campaign_id: int
    views: int = 0
    clicks: int = 0
    revenue: int = 0

@router.post("/add")
async def add_performance(data: PerformanceAdd):
    conn = db_connect()
    c = conn.cursor()
    try:
        c.execute("""CREATE TABLE IF NOT EXISTS manual_performance_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            campaign_id INTEGER,
            views INTEGER,
            clicks INTEGER,
            revenue INTEGER,
            created_at DATETIME
        )""")
        
        c.execute(
            "INSERT INTO manual_performance_events (user_id, campaign_id, views, clicks, revenue, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (data.user_id, data.campaign_id, data.views, data.clicks, data.revenue, now_text())
        )
        conn.commit()
        return {"success": True, "message": "Đã ghi nhận tracking hiệu suất thành công!"}
    except Exception as e:
        logger.error(f"Lỗi tracking: {e}")
        raise HTTPException(status_code=500, detail="Lỗi lưu số liệu")
    finally:
        conn.close()