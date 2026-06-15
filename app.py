from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi.responses import FileResponse

from config import settings
from db import init_db
import billing
import user  
import video 
import ai_media 
import campaign 
import performance
import device_ops
import report

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(billing.router, prefix="/api/v1/billing", tags=["Billing"])
app.include_router(user.router, prefix="/api/v1/user", tags=["User & Profile"])  
app.include_router(video.router, prefix="/api/v1/video", tags=["Video AI"]) 
app.include_router(ai_media.router, prefix="/api/v1/media", tags=["Media Services"]) 
app.include_router(campaign.router, prefix="/api/v1/campaign", tags=["B2C Campaign"]) 
app.include_router(performance.router, prefix="/api/v1/performance", tags=["B2C Tracking"])
app.include_router(device_ops.router, prefix="/api/v1/device-ops", tags=["B2B Device Ops"])
app.include_router(report.router, prefix="/api/v1/report", tags=["Admin Dashboard"])

# 1. Mở đường link cho trang chủ (Dashboard Báo cáo)
@app.get("/")
async def root():
    return FileResponse("index.html")

# 2. Mở đường link cho trang AI Video Generator
@app.get("/video-app")
async def video_app_ui():
    return FileResponse("video.html")

# 3. Mở đường link cho trang Quản lý Dự án B2B
@app.get("/b2b-app")
async def b2b_app_ui():
    return FileResponse("b2b.html")

# 4. Mở đường link cho trang Quản lý Affiliate B2C
@app.get("/campaign-app")
async def campaign_app_ui():
    return FileResponse("campaign.html")

# 5. Mở đường link cho trang Trạm Xử Lý Media
@app.get("/media-app")
async def media_app_ui():
    return FileResponse("media.html")