from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import logging

from config import settings
from db import init_db

# Tự động vá DB khi khởi động
import migrate_db
migrate_db.run_migration()

# Import các modules
import auth_ops
import admin_ops
import billing
import video
import coach
import device_ops
import affiliate_ops
import media_ops
import campaign_ops
import report

app = FastAPI(title="TOAN AAS OS")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ĐĂNG KÝ ROUTER ---
app.include_router(auth_ops.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(admin_ops.router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(billing.router, prefix="/api/v1/billing", tags=["Billing"])
app.include_router(video.router, prefix="/api/v1/video", tags=["Video AI"]) 
app.include_router(coach.router, prefix="/api/v1/coach", tags=["AI Coach"])
app.include_router(device_ops.router, prefix="/api/v1/device-ops", tags=["B2B"])
app.include_router(affiliate_ops.router, prefix="/api/v1/affiliate", tags=["Affiliate"])
app.include_router(media_ops.router, prefix="/api/v1/media-ops", tags=["Media"])
app.include_router(campaign_ops.router, prefix="/api/v1/campaign", tags=["Campaign"])
app.include_router(report.router, prefix="/api/v1/report", tags=["Report"])

# --- ĐIỀU HƯỚNG GIAO DIỆN ---
def get_html(file_name):
    try:
        with open(file_name, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except Exception:
        return HTMLResponse(content=f"<h1>Lỗi: Không tìm thấy giao diện {file_name}</h1>", status_code=404)

@app.get("/login")
async def login_page(): return get_html("auth.html")

@app.get("/")
async def root_page(): return get_html("index.html")

@app.get("/video-app")
async def video_app(): return get_html("video.html")

@app.get("/b2b-app")
async def b2b_app(): return get_html("b2b.html")

@app.get("/campaign-app")
async def campaign_app(): return get_html("campaign.html")

@app.get("/affiliate-app")
async def affiliate_app(): return get_html("affiliate.html")

@app.get("/media-app")
async def media_app(): return get_html("media.html")

@app.get("/coach-app")
async def coach_app(): return get_html("coach.html")

@app.get("/wallet-app")
async def wallet_app(): return get_html("wallet.html")

@app.get("/admin-app")
async def admin_page(): return get_html("admin.html")