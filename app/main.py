from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.api.health import router as health_router
from app.api.merchants import router as merchants_router
from app.api.network import router as network_router
from app.api.sms import router as sms_router
from app.api.transactions import router as transactions_router
from app.api.users import router as users_router
from app.api.wallets import router as wallets_router
from app.db import Base, engine

app = FastAPI(title="SMS Wallet Demo")
templates = Jinja2Templates(directory="app/ui/templates")
Base.metadata.create_all(bind=engine)

app.include_router(health_router)
app.include_router(sms_router)
app.include_router(users_router)
app.include_router(wallets_router)
app.include_router(transactions_router)
app.include_router(merchants_router)
app.include_router(network_router)


@app.get("/", response_class=HTMLResponse)
def mobile_demo(request: Request):
    return templates.TemplateResponse("mobile_demo.html", {"request": request, "users": [], "sms": []})


@app.get("/admin", response_class=HTMLResponse)
def admin(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request, "total_float": 0, "txns": [], "wallets": [], "sms": []})
