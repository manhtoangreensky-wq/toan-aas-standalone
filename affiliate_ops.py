from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging
from db import db_connect, now_text

router = APIRouter()
logger = logging.getLogger("TOAN_AAS_AFFILIATE")

def init_affiliate_db():
    conn = db_connect()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS affiliate_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT,
            platform TEXT,
            url TEXT,
            commission_rate TEXT,
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_affiliate_db()

class AffiliateCreate(BaseModel):
    product_name: str
    platform: str
    url: str
    commission_rate: str

@router.post("/links")
async def add_link(data: AffiliateCreate):
    try:
        conn = db_connect()
        c = conn.cursor()
        c.execute(
            "INSERT INTO affiliate_links (product_name, platform, url, commission_rate, created_at) VALUES (?, ?, ?, ?, ?)",
            (data.product_name, data.platform, data.url, data.commission_rate, now_text())
        )
        conn.commit()
        conn.close()
        return {"success": True, "message": "Thêm link thành công"}
    except Exception as e:
        logger.error(f"Lỗi thêm link Affiliate: {e}")
        raise HTTPException(status_code=500, detail="Lỗi máy chủ")

@router.get("/links")
async def get_links():
    try:
        conn = db_connect()
        c = conn.cursor()
        c.execute("SELECT id, product_name, platform, url, commission_rate, created_at FROM affiliate_links ORDER BY id DESC")
        rows = c.fetchall()
        conn.close()
        
        links = []
        for r in rows:
            links.append({
                "id": r[0], "product_name": r[1], "platform": r[2], 
                "url": r[3], "commission_rate": r[4], "created_at": r[5]
            })
        return {"success": True, "data": links}
    except Exception as e:
        logger.error(f"Lỗi tải link Affiliate: {e}")
        return {"success": False, "data": []}