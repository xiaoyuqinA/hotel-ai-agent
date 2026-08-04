"""Admin 后台 — 邀请码管理。"""

import secrets
import string
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from shared.invite.service import get_connection, validate_invite_code

app = FastAPI(title="Hotel AI Admin")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

get_db = get_connection  # 别名，保持已有代码兼容


def generate_code(length=12) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "INVITE-" + "".join(secrets.choice(alphabet) for _ in range(length))


@app.on_event("startup")
async def startup():
    conn = await get_db()
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS invite_codes (
                code VARCHAR(32) PRIMARY KEY,
                hotel_id VARCHAR(64),
                user_name VARCHAR(128),
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                expires_at TIMESTAMP WITH TIME ZONE NOT NULL
            )
        """)
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_invite_codes_expires ON invite_codes(expires_at)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_invite_codes_active ON invite_codes(is_active)")
    finally:
        await conn.close()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    conn = await get_db()
    try:
        rows = await conn.fetch(
            "SELECT code, hotel_id, user_name, is_active, created_at, expires_at "
            "FROM invite_codes ORDER BY created_at DESC"
        )
    finally:
        await conn.close()
    return templates.TemplateResponse(request, "index.html", {"codes": rows, "now": datetime.now(timezone.utc)})


@app.get("/generate", response_class=HTMLResponse)
async def generate_page(request: Request):
    return templates.TemplateResponse(request, "generate.html", {})


@app.get("/requests", response_class=HTMLResponse)
async def requests_page(request: Request):
    """查看官网邀请码申请记录。"""
    conn = await get_db()
    try:
        rows = await conn.fetch(
            "SELECT id, name, phone, created_at "
            "FROM invite_requests ORDER BY id DESC"
        )
    finally:
        await conn.close()
    return templates.TemplateResponse(request, "requests.html", {"requests": rows})


@app.post("/generate")
async def generate_action(
    hotel_id: str = Form(""),
    user_name: str = Form(""),
    days: int = Form(7),
):
    code = generate_code()
    expires_at = datetime.now(timezone.utc) + timedelta(days=days)

    conn = await get_db()
    try:
        await conn.execute(
            "INSERT INTO invite_codes (code, hotel_id, user_name, expires_at) VALUES ($1, $2, $3, $4)",
            code, hotel_id or None, user_name or None, expires_at,
        )
    finally:
        await conn.close()

    return RedirectResponse(url="/", status_code=303)


@app.post("/deactivate")
async def deactivate(code: str = Form(...)):
    conn = await get_db()
    try:
        await conn.execute("UPDATE invite_codes SET is_active = false WHERE code = $1", code)
    finally:
        await conn.close()
    return RedirectResponse(url="/", status_code=303)


@app.post("/activate")
async def activate(code: str = Form(...)):
    conn = await get_db()
    try:
        await conn.execute("UPDATE invite_codes SET is_active = true WHERE code = $1", code)
    finally:
        await conn.close()
    return RedirectResponse(url="/", status_code=303)


@app.post("/delete")
async def delete(code: str = Form(...)):
    conn = await get_db()
    try:
        await conn.execute("DELETE FROM invite_codes WHERE code = $1", code)
    finally:
        await conn.close()
    return RedirectResponse(url="/", status_code=303)
