
from fastapi import FastAPI, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
import json, sqlite3, os, datetime, random

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Load prompts
with open("prompts.json", "r", encoding="utf-8") as f:
    PROMPTS = json.load(f)

# DB - use Railway volume
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

# Load multiple keys
def get_api_keys():
    keys = []
    # OpenAI keys: OPENAI_API_KEY, OPENAI_API_KEY_2, OPENAI_API_KEY_3...
    for k, v in os.environ.items():
        if k.startswith("OPENAI_API_KEY") and v and v.startswith("sk-"):
            keys.append(("openai", v))
    # Gemini keys
    for k, v in os.environ.items():
        if k.startswith("GEMINI_API_KEY") and v:
            keys.append(("gemini", v))
    return keys

API_KEYS = get_api_keys()

def generate_with_openai(prompt, api_key):
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content": prompt}],
            max_tokens=800
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"[OpenAI lỗi: {e}]"

def generate_with_gemini(prompt, api_key):
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        resp = model.generate_content(prompt)
        return resp.text
    except Exception as e:
        return f"[Gemini lỗi: {e}]"

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(request, "index.html", {
        "request": request,
        "prompts": PROMPTS,
        "keys_count": len(API_KEYS)
    })

@app.post("/generate")
async def generate(prompt: str = Form(...)):
    if not API_KEYS:
        result = f"✅ Demo: '{prompt}'\n\n(Chưa có API key - thêm OPENAI_API_KEY hoặc GEMINI_API_KEY vào Shared Variables)"
        model_used = "demo"
    else:
        provider, key = random.choice(API_KEYS)
        if provider == "openai":
            result = generate_with_openai(prompt, key)
            model_used = "openai"
        else:
            result = generate_with_gemini(prompt, key)
            model_used = "gemini"

    conn.execute(
        "INSERT INTO history (prompt, result, model, created_at) VALUES (?, ?, ?, ?)",
        (prompt, result, model_used, datetime.datetime.now().isoformat())
    )
    conn.commit()

    return JSONResponse({"result": result, "model": model_used})

@app.get("/history")
async def history():
    cur = conn.execute("SELECT prompt, result, model, created_at FROM history ORDER BY id DESC LIMIT 50")
    rows = [{"prompt": r[0], "result": r[1], "model": r[2], "time": r[3]} for r in cur.fetchall()]
    return JSONResponse(rows)
