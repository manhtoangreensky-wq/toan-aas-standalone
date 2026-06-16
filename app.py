from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import os
from datetime import datetime

from config import settings
from db import init_db, db_connect
from security import is_admin_user

# Chạy vá lỗi DB ngay khi khởi động
try:
    import migrate_db
    migrate_db.run_migration()
except Exception as e:
    print("Bỏ qua migrate_db:", e)

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
import ai_assistant
import customer_api
import performance

app = FastAPI(title="TOAN AAS Control Center")

def cors_allow_origins() -> list[str]:
    raw = os.environ.get("CORS_ALLOW_ORIGINS", "https://app.toanaas.vn,https://toanaas.vn")
    origins = [item.strip() for item in raw.split(",") if item.strip()]
    return origins or ["https://app.toanaas.vn", "https://toanaas.vn"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allow_origins(),
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
app.include_router(ai_assistant.router, prefix="/api/v1/assistant", tags=["AI Assistant"])
app.include_router(customer_api.router, prefix="/api/v1/customer", tags=["Customer Web App"])
app.include_router(performance.router, prefix="/api/v1/performance", tags=["Performance"])

# Hàm hiển thị giao diện an toàn
def get_html(file_name):
    try:
        with open(file_name, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except Exception:
        return HTMLResponse(content=f"<h3 style='color:red; text-align:center; margin-top:50px;'>Lỗi 404: Không tìm thấy file {file_name}</h3>", status_code=404)

# -----------------------------------------------------
# 1. API ĐĂNG NHẬP (Xác thực ID qua Database)
# -----------------------------------------------------
class LoginReq(BaseModel):
    user_id: str

@app.post("/api/v1/auth/login")
async def login_api(data: LoginReq):
    conn = db_connect()
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE user_id=?", (data.user_id,))
    user = c.fetchone()
    conn.close()
    
    if user:
        role = "admin" if is_admin_user(data.user_id) else "user"
        
        return {
            "success": True, 
            "role": role,
            "username": user[0],
            "user_id": data.user_id
        }
    else:
        return {"success": False, "message": "Tài khoản chưa tồn tại! Hãy vào Bot Telegram gõ /start trước."}

@app.get("/health")
async def health():
    db_status = "ok"
    try:
        conn = db_connect()
        conn.execute("SELECT 1")
        conn.close()
    except Exception:
        db_status = "error"
    return {
        "ok": db_status == "ok",
        "app": "TOAN AAS Control Center",
        "domain": "app.toanaas.vn",
        "entrypoint": "app.py",
        "db": db_status,
        "time": datetime.utcnow().isoformat() + "Z",
    }

@app.get("/api/v1/health")
async def api_health():
    return await health()

# -----------------------------------------------------
# 2. ĐỊNH TUYẾN GIAO DIỆN WEB (ĐÃ CHUẨN GATE CHECK)
# -----------------------------------------------------
@app.get("/login")
async def login_page(): return get_html("login.html")

@app.get("/")
async def root_page(): return get_html("customer_app.html")

@app.get("/admin-app")
async def admin_page(): return get_html("admin.html")

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

@app.get("/app")
async def mobile_app_ui(): return get_html("mobile_app.html")

@app.get("/assistant-app")
async def assistant_app_ui(): return get_html("mobile_chat.html")
