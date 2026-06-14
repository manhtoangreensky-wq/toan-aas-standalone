
"""
TOAN AAS WEB STANDALONE - Tách từ bot.py V15.2
Chạy độc lập, không cần Telegram
"""
import os, json, sqlite3, datetime, random, asyncio
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, FileResponse
from openai import OpenAI

app = FastAPI(title="TOAN AAS Web")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# DB
DB_PATH = os.getenv("DB_PATH", "/data/toan_aas_web.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.execute("""CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY, module TEXT, prompt TEXT, result TEXT, created_at TEXT
)""")
conn.commit()

def get_keys():
    keys = []
    for k,v in os.environ.items():
        if k.startswith("OPENAI_API_KEY") and v.startswith("sk-"): keys.append(("openai",v))
        if k.startswith("GEMINI_API_KEY") and len(v)>20: keys.append(("gemini",v))
    return keys

KEYS = get_keys()

async def ai_generate(prompt, system="Bạn là trợ lý TOAN AAS"):
    if not KEYS:
        return f"[DEMO] {prompt}"
    provider,key = random.choice(KEYS)
    try:
        if provider=="openai":
            client = OpenAI(api_key=key)
            r = client.chat.completions.create(model="gpt-4o-mini",
                messages=[{"role":"system","content":system},{"role":"user","content":prompt}], max_tokens=1000)
            return r.choices[0].message.content
        else:
            import google.generativeai as genai
            genai.configure(api_key=key)
            model = genai.GenerativeModel("gemini-1.5-flash-latest")
            return model.generate_content(prompt).text
    except Exception as e:
        return f"Lỗi: {e}"

def log(module, prompt, result):
    conn.execute("INSERT INTO history VALUES (NULL,?,?,?,?)",
        (module,prompt,result,datetime.datetime.now().isoformat()))
    conn.commit()

@app.get("/")
async def home(request: Request):
    modules = [
        {"id":"content","icon":"🎬","name":"Tạo nội dung","desc":"Kịch bản video, caption, hashtag"},
        {"id":"ai","icon":"🤖","name":"Hỏi AI","desc":"Viết bài, ý tưởng, code"},
        {"id":"docs","icon":"📄","name":"Tài liệu","desc":"PDF sang Word, ảnh sang PDF"},
        {"id":"image","icon":"🖼","name":"Hình ảnh","desc":"Tạo ảnh AI, tách nền"},
        {"id":"music","icon":"🎵","name":"Nhạc / SFX","desc":"Tìm nhạc, tạo prompt"},
        {"id":"voice","icon":"🎤","name":"Voice","desc":"TTS, bóc băng audio"},
        {"id":"translate","icon":"🌐","name":"Dịch thuật","desc":"Dịch văn bản, phụ đề"},
        {"id":"memory","icon":"🧠","name":"Ghi nhớ","desc":"Lưu ghi chú, nhắc việc"},
        {"id":"xu","icon":"💳","name":"Xu dịch vụ","desc":"Nạp Xu, bảng giá"},
    ]
    return templates.TemplateResponse("dashboard.html", {"request":request,"modules":modules,"keys":len(KEYS)})

@app.post("/api/generate")
async def generate(module: str = Form(...), prompt: str = Form(...)):
    systems = {
        "content":"Bạn là chuyên gia content marketing Việt Nam",
        "ai":"Bạn là trợ lý AI đa năng",
        "image":"Bạn tạo prompt ảnh Midjourney chi tiết",
        "voice":"Bạn viết kịch bản voice",
        "translate":"Bạn dịch chính xác",
    }
    result = await ai_generate(prompt, systems.get(module,"Bạn là TOAN AAS"))
    log(module,prompt,result)
    return {"result":result}

@app.get("/api/history")
async def history():
    cur = conn.execute("SELECT module,prompt,result,created_at FROM history ORDER BY id DESC LIMIT 50")
    return [{"module":r[0],"prompt":r[1],"result":r[2],"time":r[3][:16]} for r in cur.fetchall()]

# Run
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT","8000")))
