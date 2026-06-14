from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import settings
from db import init_db
import billing
import user  
import video # <--- THÊM DÒNG NÀY: Import module video

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

# Cắm điện cho các module
app.include_router(billing.router, prefix="/api/v1/billing", tags=["Billing"])
app.include_router(user.router, prefix="/api/v1/user", tags=["User"])  
app.include_router(video.router, prefix="/api/v1/video", tags=["Video AI"]) # <--- THÊM DÒNG NÀY

@app.get("/")
async def root():
    return {"status": "online", "message": "App đang chạy ngon lành nhé!"}