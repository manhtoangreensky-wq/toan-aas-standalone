from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi.responses import FileResponse, RedirectResponse

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
import auth 
import coach
import device_ops
import affiliate_ops
import media_ops
import migrate_db
migrate_db.run_migration()
import migrate_db
import billing

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

# --- TRẠM GÁC BẢO VỆ (MIDDLEWARE) ---
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    
    # Cho phép đi qua nếu là gọi API, vào trang Login, hoặc xem file Docs
    if path.startswith("/api/") or path == "/login" or path == "/docs" or path == "/openapi.json":
        return await call_next(request)

    # Bắt buộc kiểm tra Thẻ Cookie khi vào giao diện
    token = request.cookies.get("admin_token")
    if not token:
        return RedirectResponse(url="/login")

    return await call_next(request)

# --- CÁC ROUTER API ---
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Security"]) 
app.include_router(billing.router, prefix="/api/v1/billing", tags=["Billing"])
app.include_router(user.router, prefix="/api/v1/user", tags=["User & Profile"])  
app.include_router(video.router, prefix="/api/v1/video", tags=["Video AI"]) 
app.include_router(ai_media.router, prefix="/api/v1/media", tags=["Media Services"]) 
app.include_router(campaign.router, prefix="/api/v1/campaign", tags=["B2C Campaign"]) 
app.include_router(performance.router, prefix="/api/v1/performance", tags=["B2C Tracking"])
app.include_router(device_ops.router, prefix="/api/v1/device-ops", tags=["B2B Device Ops"])
app.include_router(report.router, prefix="/api/v1/report", tags=["Admin Dashboard"])
app.include_router(coach.router, prefix="/api/v1/coach", tags=["AI Growth Coach"])
app.include_router(device_ops.router, prefix="/api/v1/device-ops", tags=["B2B"])
app.include_router(affiliate_ops.router, prefix="/api/v1/affiliate", tags=["Affiliate"])
app.include_router(media_ops.router, prefix="/api/v1/media-ops", tags=["Media"])
app.include_router(billing.router, prefix="/api/v1/billing", tags=["Billing"])

# --- ĐƯỜNG LINK GIAO DIỆN ---
@app.get("/login")
async def login_ui():
    return FileResponse("login.html")

@app.get("/")
async def root():
    return FileResponse("index.html")

@app.get("/video-app")
async def video_app_ui():
    return FileResponse("video.html")

@app.get("/b2b-app")
async def b2b_app_ui():
    return FileResponse("b2b.html")

@app.get("/campaign-app")
async def campaign_app_ui():
    return FileResponse("campaign.html")

@app.get("/media-app")
async def media_app_ui():
    return FileResponse("media.html")

@app.get("/coach-app")
async def coach_app_ui():
    return FileResponse("coach.html")

@app.get("/wallet-app")
async def wallet_app_ui():
    return FileResponse("wallet.html")

@app.get("/b2b-app")
async def b2b_app():
    with open("b2b.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/affiliate-app")
async def affiliate_app():
    with open("affiliate.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/media-app")
async def media_app():
    with open("media.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/wallet-app")
async def wallet_app():
    with open("wallet.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())