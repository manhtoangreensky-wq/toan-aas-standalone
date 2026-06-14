from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import logging

router = APIRouter()
logger = logging.getLogger("TOAN_AAS_MEDIA")

# Tự động lấy các Key sếp đã nạp trên Railway
DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY", "")
FISH_AUDIO_KEY = os.environ.get("FISH_AUDIO_KEY", "")
CUTOUT_API_KEY = os.environ.get("CUTOUT_API_KEY", "")

# --- CÁC MODEL DỮ LIỆU ĐẦU VÀO ---
class TTSRequest(BaseModel):
    text: str
    voice_id: str = "default_voice"

class STTRequest(BaseModel):
    audio_url: str

class ImageRequest(BaseModel):
    image_url: str

# --- 1. API TEXT TO SPEECH (Lồng tiếng) ---
@router.post("/tts")
async def text_to_speech(request: TTSRequest):
    """API chuyển văn bản thành giọng nói (Gọi Fish Audio hoặc ElevenLabs)"""
    if not FISH_AUDIO_KEY:
        raise HTTPException(status_code=500, detail="Hệ thống chưa nạp FISH_AUDIO_KEY")
    
    # Tại đây App sẽ gọi request đến API của Fish Audio
    # Trả về kết quả cho Web/App hiển thị
    return {
        "success": True,
        "provider": "fish_audio",
        "action": "text_to_speech",
        "text_length": len(request.text),
        "message": "Đã tiếp nhận yêu cầu lồng tiếng thành công!",
        "mock_audio_url": "https://api.toanaas.com/temp/audio_123.mp3" # Link giả lập để Web test giao diện
    }

# --- 2. API SPEECH TO TEXT (Bóc băng) ---
@router.post("/stt")
async def speech_to_text(request: STTRequest):
    """API bóc băng ghi âm (Gọi Deepgram)"""
    if not DEEPGRAM_API_KEY:
        raise HTTPException(status_code=500, detail="Hệ thống chưa nạp DEEPGRAM_API_KEY")
    
    return {
        "success": True,
        "provider": "deepgram",
        "action": "speech_to_text",
        "source_url": request.audio_url,
        "message": "Đã bóc băng thành công!",
        "mock_transcript": "Xin chào, đây là đoạn văn bản được bóc băng từ hệ thống Deepgram của TOAN AAS."
    }

# --- 3. API REMOVE BACKGROUND (Tách nền) ---
@router.post("/remove-bg")
async def remove_background(request: ImageRequest):
    """API tách nền ảnh (Gọi Cutout)"""
    if not CUTOUT_API_KEY:
        raise HTTPException(status_code=500, detail="Hệ thống chưa nạp CUTOUT_API_KEY")
    
    return {
        "success": True,
        "provider": "cutout",
        "action": "remove_background",
        "message": "Đã tách nền thành công!",
        "mock_processed_image": "https://api.toanaas.com/temp/nobg_123.png"
    }