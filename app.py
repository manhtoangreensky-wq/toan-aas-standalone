from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from config import settings
from db import init_db

# Chạy vá lỗi DB ngay khi khởi động
import migrate_db
migrate_db.run_migration()

# Gọi các module
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
import erp_core

app = FastAPI(title="TOAN AAS OS")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký API
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
app.include_router(erp_core.router, prefix="/api/v1/erp", tags=["ERP Core"])

# Hàm hiển thị giao diện an toàn
def get_html(file_name):
    try:
        with open(file_name, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except Exception:
        return HTMLResponse(content=f"<h3 style='color:red; text-align:center; margin-top:50px;'>Lỗi 404: Không tìm thấy file {file_name}</h3>", status_code=404)

# Khai báo đường link (Mỗi link chỉ khai báo 1 lần duy nhất)
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