import os
from dotenv import load_dotenv

# Maxfiy sozlamalarni .env faylidan yuklash (boshqa importlardan oldin bo'lishi shart)
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

from fastapi import FastAPI, UploadFile, File, Request, Depends, HTTPException, Cookie, Response, Form, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from config import SYSTEM_PROMPT
import database
import auth
import api
import stats_client

from PIL import Image
import base64
import json
import io
import os
import jwt
import uuid
from datetime import datetime

def run_image_search(file_path: str):
    from trained_model.search import search
    return search(file_path)

database.init_db()

app = FastAPI(title="EndoAI - Medical Imaging Analysis")
app.mount("/static", StaticFiles(directory="frontendnew/static"), name="static")
app.mount("/uploads", StaticFiles(directory=database.UPLOADS_DIR), name="uploads")

templates = Jinja2Templates(directory='frontendnew')

# Auth logic and routes moved to auth.py
app.include_router(auth.router)
app.include_router(api.router)

def get_current_user(access_token: str = Cookie(None)):
    return auth.get_user_from_token(access_token)

def get_current_admin(access_token: str = Cookie(None)):
    user = auth.get_user_from_token(access_token)
    if not user or user.get("role") != "admin":
        return None
    return user

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.1,
    api_key=os.getenv("GOOGLE_API_KEY"),
    response_mime_type="application/json"
)

origins = ['*']

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Protected Routes ---

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse(request, "index.html", {"user": user})

@app.get("/analyze", response_class=HTMLResponse)
async def analyze_page(request: Request, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(request, "analyze.html", {"user": user})

@app.get("/news", response_class=HTMLResponse)
async def news_page(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse(request, "news.html", {"user": user})

@app.get("/history_page", response_class=HTMLResponse)
async def history_page_view(request: Request, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(request, "history.html", {"user": user})

@app.get("/dashboard", response_class=HTMLResponse)
async def user_dashboard(request: Request, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(
        request,
        "user_dashboard.html",
        {
            "user": user,
            "section": "snapshot",
        },
    )

@app.get("/dashboard/{section}", response_class=HTMLResponse)
async def user_dashboard_section(section: str, request: Request, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(
        request,
        "user_dashboard.html",
        {
            "user": user,
            "section": stats_client.normalize_section("user", section),
        },
    )

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, user=Depends(get_current_admin)):
    if not user:
        return RedirectResponse(url="/admin-login", status_code=303)
    return templates.TemplateResponse(
        request,
        "admin.html",
        {
            "user": user,
            "section": "dashboard",
        },
    )

@app.get("/admin/{section}", response_class=HTMLResponse)
async def admin_dashboard_section(section: str, request: Request, user=Depends(get_current_admin)):
    if not user:
        return RedirectResponse(url="/admin-login", status_code=303)
    return templates.TemplateResponse(
        request,
        "admin.html",
        {
            "user": user,
            "section": stats_client.normalize_section("admin", section),
        },
    )

@app.get("/api/stats/{scope}/{section}")
def stats_proxy(scope: str, section: str, user=Depends(get_current_user)):
    if scope not in {"admin", "user"}:
        raise HTTPException(status_code=404, detail="Statistika bo'limi topilmadi")
    if not user:
        raise HTTPException(status_code=401)
    if scope == "admin" and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin huquqi kerak")
    return stats_client.get_stats(scope, section, user=user)

@app.get("/api/internal/stats-snapshot")
def internal_stats_snapshot(request: Request, user_id: int | None = None, x_internal_stats_key: str | None = Header(None)):
    client_host = request.client.host if request.client else ""
    allowed_hosts = {"127.0.0.1", "::1", "localhost"}
    if client_host not in allowed_hosts:
        raise HTTPException(status_code=403, detail="Only local stats service can read this endpoint")
    if x_internal_stats_key != stats_client.get_internal_stats_key():
        raise HTTPException(status_code=403, detail="Invalid internal stats key")
    return stats_client.get_encoded_stats_snapshot(user_id=user_id)

from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": str(exc.body)},
    )

@app.post("/predict")
async def predict(
    file: UploadFile = File(...), 
    age: str = Form(...),
    gender: str = Form(...),
    user = Depends(get_current_user)
):
    if not user:
        raise HTTPException(status_code=401)

    try:
        age_int = int(age)
    except ValueError:
        raise HTTPException(status_code=422, detail="Bemor yoshi butun son bo'lishi kerak")

    image_bytes = await file.read()
    file_ext = file.filename.split(".")[-1]
    file_name = f"{uuid.uuid4()}.{file_ext}"
    file_path = os.path.join(database.UPLOADS_DIR, file_name)
    
    with open(file_path, "wb") as f:
        f.write(image_bytes)

    try:
        # 1. Search using the local CLIP model
        search_result = run_image_search(file_path)
        
        if "error" in search_result:
            return JSONResponse(status_code=500, content={"error": search_result["error"]})

        disease = search_result["disease"]
        confidence = int(search_result["confidence"])

        # 2. Use Gemini to generate description and recommendations based on results and patient info
        prompt = f"""
        Bemor haqida ma'lumot:
        - Yoshi: {age_int}
        - Jinsi: {gender}
        
        Endoskopik tahlil natijasi (CLIP model orqali):
        - Aniqlangan holat: {disease}
        - Aniqlik darajasi: {confidence}%
        
        Siz tajribali gastroenterologsiz. Ushbu ma'lumotlarga asoslanib, bemor uchun o'zbek tilida:
        1. Qisqa va lo'nda klinik tavsif (description) yozing.
        2. Kamida 3-4 ta foydali tavsiya (recommendation) bering.
        
        Javobni FAQAT JSON formatida qaytaring:
        {{
            "description": "...",
            "recommendation": ["...", "...", ...]
        }}
        """

        messages = [
            SystemMessage(content="Siz tibbiy tahlillarni sharhlovchi professional shifokorsiz. Javobni faqat o'zbek tilida va JSON formatida qaytaring."),
            HumanMessage(content=prompt),
        ]
        
        response = await llm.agenerate([messages])
        gemini_result_text = response.generations[0][0].text.strip()
        
        # Clean JSON if necessary
        if "```json" in gemini_result_text:
            gemini_result_text = gemini_result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in gemini_result_text:
            gemini_result_text = gemini_result_text.split("```")[1].strip()
            
        gemini_json = json.loads(gemini_result_text)

        result_json = {
            "disease": disease,
            "confidence": confidence,
            "description": gemini_json.get("description", ""),
            "recommendation": gemini_json.get("recommendation", []),
            "patient_info": {
                "age": age,
                "gender": gender
            }
        }
        
        # Save to history
        database.add_history_item(user["id"], f"/uploads/{file_name}", json.dumps(result_json))

        return JSONResponse(content=result_json)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/history")
async def get_history(user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401)
    
    # Get history from database function
    rows = database.get_user_history(user["id"])
    
    return [{
        "id": r["id"], "image_path": r["image_path"], 
        "result": json.loads(r["result_json"]), "timestamp": r["timestamp"]
    } for r in rows]
