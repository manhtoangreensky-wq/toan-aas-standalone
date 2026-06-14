from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os

# Khởi tạo TOAN AAS Core API
app = FastAPI(
    title="TOAN AAS Core Backend",
    description="API phục vụ Web Dashboard và Mobile App",
    version="1.0.0"
)

# Cấu hình CORS để Web (React/NextJS) gọi API không bị lỗi
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Trên production sẽ đổi thành domain web của sếp
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MODELS CƠ BẢN ---
class StatusResponse(BaseModel):
    status: str
    version: str
    message: str

# --- ROUTES ---
@app.get("/", tags=["Root"])
async def root():
    return {"message": "TOAN AAS Core Backend is running. Please use /api/v1 endpoints."}

@app.get("/api/health", response_model=StatusResponse, tags=["Health"])
async def health_check():
    """Kiểm tra sức khỏe hệ thống cho Railway"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "message": "Database and AI providers pending initialization"
    }

# Các Route này sẽ do Antigravity viết chi tiết để sếp lắp vào sau
# app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
# app.include_router(billing_router, prefix="/api/v1/billing", tags=["Billing & PayOS"])
# app.include_router(ai_router, prefix="/api/v1/ai", tags=["AI Services"])