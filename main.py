from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.db import init_db
from app.api.v1 import billing
from contextlib import asynccontextmanager

# Chạy init_db khi khởi động app
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Lõi API hệ thống TOAN AAS - Headless Architecture",
    lifespan=lifespan
)

# Cấu hình CORS để Web App (React/Vue) gọi API không bị lỗi
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Có thể giới hạn domain của sếp sau này
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gắn các Module (Routers) vào
app.include_router(billing.router, prefix="/api/v1/billing", tags=["Billing & PayOS"])

@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "online",
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "message": "Core Backend is running perfectly!"
    }