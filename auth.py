from fastapi import APIRouter, Request, Form, Depends, Response, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import os
import hashlib
import jwt
import json
from datetime import datetime, timedelta
import database

router = APIRouter()
templates = Jinja2Templates(directory='frontendnew')

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY .env faylida sozlanmagan. Iltimos .env faylini to'ldiring."
    )
ALGORITHM = "HS256"

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def create_login_response(request: Request, user, redirect_url: str, error_template: str, required_role: str | None = None):
    if required_role and user["role"] != required_role:
        error = "Bu sahifa uchun ruxsat yo'q."
        if "application/json" in request.headers.get("Accept", ""):
            return {"error": error}
        return templates.TemplateResponse(request, error_template, {"error": error})

    expire = datetime.utcnow() + timedelta(hours=24)
    to_encode = {
        "sub": user["username"],
        "id": user["id"],
        "role": user["role"],
        "exp": expire,
    }
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    database.add_session(user["id"], token, expire)

    if "application/json" in request.headers.get("Accept", ""):
        res = {"success": True, "username": user["username"], "role": user["role"]}
        resp = Response(content=json.dumps(res), media_type="application/json")
        resp.set_cookie(key="access_token", value=token, httponly=True)
        return resp

    redir = RedirectResponse(url=redirect_url, status_code=303)
    redir.set_cookie(key="access_token", value=token, httponly=True)
    return redir

def get_user_from_token(access_token: str | None):
    if not access_token:
        return None
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        return None

    session = database.get_active_session(access_token)
    if not session or session["user_id"] != payload.get("id"):
        return None

    return {
        "id": session["user_id"],
        "sub": session["username"],
        "username": session["username"],
        "role": session["role"],
    }

def require_admin_user(access_token: str = Cookie(None)):
    user = get_user_from_token(access_token)
    if not user or user.get("role") != "admin":
        return None
    return user

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")

@router.post("/login")
async def login(request: Request, response: Response, username: str = Form(...), password: str = Form(...)):
    user = database.get_user_by_username(username)
    
    if not user or not verify_password(password, user["password"]):
        if "application/json" in request.headers.get("Accept", ""):
             return {"error": "Noto'g'ri username yoki parol"}
        return templates.TemplateResponse(request, "login.html", {"error": "Noto'g'ri username yoki parol"})

    return create_login_response(request, user, "/", "login.html", required_role="user")

@router.get("/admin-login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    return templates.TemplateResponse(request, "admin_login.html")

@router.post("/admin-login")
async def admin_login(request: Request, username: str = Form(...), password: str = Form(...)):
    user = database.get_user_by_username(username)
    if not user or not verify_password(password, user["password"]):
        return templates.TemplateResponse(request, "admin_login.html", {"error": "Noto'g'ri admin login yoki parol"})

    return create_login_response(request, user, "/admin", "admin_login.html", required_role="admin")

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html")

@router.post("/register")
async def register(request: Request, username: str = Form(...), password: str = Form(...)):
    hashed_password = hash_password(password)
    success = database.add_user(username, hashed_password, role="user")
    
    if success:
        if "application/json" in request.headers.get("Accept", ""):
            return {"success": True}
        return RedirectResponse(url="/login", status_code=303)
    else:
        if "application/json" in request.headers.get("Accept", ""):
            return {"error": "Username band yoki tizim xatosi"}
        return templates.TemplateResponse(request, "register.html", {"error": "Username band yoki tizim xatosi"})

@router.get("/logout")
async def logout(access_token: str = Cookie(None)):
    if access_token:
        database.revoke_session(access_token)
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("access_token")
    return response
