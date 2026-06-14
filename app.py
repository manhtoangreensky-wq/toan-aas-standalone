
from fastapi import FastAPI, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
import json, sqlite3, os, datetime, random

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

with open("prompts.json", "r", encoding="utf-8") as f:
    PROMPTS = json.load(f)

DB_PATH = os.getenv("DB_PATH", "/data/toan_aas.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.execute("""
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt TEXT,
    result TEXT,
    model TEXT,
    created_at TEXT
)
""")
conn.commit()

def get_api_keys():
    keys = []
    for k, v in os.environ.items():
        if k.startswith("OPENAI_API_KEY") and v and v.startswith("sk-"):
            keys.append(("openai", v))
    for k, v in os.environ.items():
        if k.startswith("GEMINI_API_KEY") and v and len(v) > 20:
            keys.append(("gemini", v))
    return keys

API_KEYS = get_api_keys()

def generate_with_openai(prompt, api_key):
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content": "Bạn là trợ lý content marketing Việt Nam. Trả lời ngắn gọn, thực tế: " + prompt}],
            max_tokens=900
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"[OpenAI lỗi: {e}]"

def generate_with_gemini(prompt, api_key):
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        # Fix model name
        model = genai.GenerativeModel("gemini-1.5-flash-latest")
        resp = model.generate_content(prompt)
        return resp.text
    except Exception as e:
        # fallback to pro
        try:
            model = genai.GenerativeModel("gemini-pro")
            resp = model.generate_content(prompt)
            return resp.text
        except Exception as e2:
            return f"[Gemini lỗi: {e2}]"

@app.get("/")
async def home(request: Request):
    cur = conn.execute("SELECT COUNT(*) FROM history")
    total = cur.fetchone()[0]
    cur = conn.execute("SELECT COUNT(DISTINCT date(created_at)) FROM history")
    days = cur.fetchone()[0] or 1
    return templates.TemplateResponse(request, "index.html", {
        "request": request,
        "prompts": PROMPTS,
        "keys_count": len(API_KEYS),
        "total": total,
        "avg_per_day": round(total/days,1)
    })

@app.post("/generate")
async def generate(prompt: str = Form(...)):
    if not API_KEYS:
        result = f"Demo: {prompt}\n\nThêm OPENAI_API_KEY hoặc GEMINI_API_KEY vào Shared Variables để dùng AI thật."
        model_used = "demo"
    else:
        provider, key = random.choice(API_KEYS)
        if provider == "openai":
            result = generate_with_openai(prompt, key)
            model_used = "openai"
        else:
            result = generate_with_gemini(prompt, key)
            model_used = "gemini"
            if "lỗi" in result.lower() and any(k[0]=="openai" for k in API_KEYS):
                # auto fallback
                o_key = [k[1] for k in API_KEYS if k[0]=="openai"][0]
                result = generate_with_openai(prompt, o_key)
                model_used = "openai-fallback"

    conn.execute(
        "INSERT INTO history (prompt, result, model, created_at) VALUES (?, ?, ?, ?)",
        (prompt, result, model_used, datetime.datetime.now().isoformat())
    )
    conn.commit()
    return JSONResponse({"result": result, "model": model_used})

@app.get("/history")
async def history():
    cur = conn.execute("SELECT prompt, result, model, created_at FROM history ORDER BY id DESC LIMIT 100")
    rows = [{"prompt": r[0], "result": r[1], "model": r[2], "time": r[3][:16].replace("T"," ")} for r in cur.fetchall()]
    return JSONResponse(rows)

@app.get("/stats")
async def stats():
    cur = conn.execute("SELECT model, COUNT(*) FROM history GROUP BY model")
    by_model = {r[0]: r[1] for r in cur.fetchall()}
    cur = conn.execute("SELECT date(created_at) as d, COUNT(*) FROM history GROUP BY d ORDER BY d DESC LIMIT 7")
    by_day = [{"date": r[0], "count": r[1]} for r in cur.fetchall()][::-1]
    return JSONResponse({"by_model": by_model, "by_day": by_day})
