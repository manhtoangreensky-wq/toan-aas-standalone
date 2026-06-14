
from fastapi import FastAPI, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
import json, sqlite3, os, datetime

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Load prompts
PROMPTS_FILE = "prompts.json"
if os.path.exists(PROMPTS_FILE):
    with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
        PROMPTS = json.load(f)
else:
    PROMPTS = ["Viết bài bán hàng cho sản phẩm skincare", "Tạo kịch bản video 30s"]

# DB init (Railway writable)
DB_PATH = "/data/toan_aas.db"
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.execute("""
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt TEXT,
    result TEXT,
    created_at TEXT
)
""")
conn.commit()

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(request, "index.html", {
        "request": request,
        "prompts": PROMPTS
    })

@app.post("/generate")
async def generate(prompt: str = Form(...)):
    # Demo generation - thay bằng API AI thật sau
    result = f"✅ Kết quả cho: '{prompt}'\n\nĐây là bản demo. Bạn có thể tích hợp OpenAI/Gemini ở đây."

    conn.execute(
        "INSERT INTO history (prompt, result, created_at) VALUES (?, ?, ?)",
        (prompt, result, datetime.datetime.now().isoformat())
    )
    conn.commit()

    return JSONResponse({"result": result})

@app.get("/history")
async def history():
    cur = conn.execute("SELECT prompt, result, created_at FROM history ORDER BY id DESC LIMIT 20")
    rows = [{"prompt": r[0], "result": r[1], "time": r[2]} for r in cur.fetchall()]
    return JSONResponse(rows)
