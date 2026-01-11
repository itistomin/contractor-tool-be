from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.requests import Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from views import (
    authorization_router,
)


load_dotenv()


app = FastAPI()


app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="static")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/cognito-auth", response_class=HTMLResponse)
async def cognito_auth(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/health")
async def get_health():
    return {"status": "ok"}


app.include_router(authorization_router, prefix="/api")
