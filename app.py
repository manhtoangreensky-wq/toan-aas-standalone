import os, json, sqlite3
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

DB_FILE = os.getenv("DB_FILE", "web.db")
PROMPTS_FILE = "prompts.json"

# init db
conn = sqlite3.connect(DB_FILE)
conn.execute("""CREATE TABLE IF NOT EXISTS usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)""")
conn.commit()
conn.close()

def load_prompts():
    if os.path.exists(PROMPTS_FILE):
        with open(PROMPTS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    prompts = load_prompts()
    return templates.TemplateResponse("index.html", {"request": request, "prompts": prompts})

@app.post("/generate")
async def generate(prompt: str = Form(...)):
    # lưu lịch sử
    conn = sqlite3.connect(DB_FILE)
    conn.execute("INSERT INTO usage (prompt) VALUES (?)", (prompt,))
    conn.commit()
    conn.close()
    # giả lập kết quả (thay bằng Gemini sau)
    return JSONResponse({"result": f"Prompt đã nhận: {prompt}", "status": "ok"})

@app.get("/health")
def health():
    return {"ok": True}
