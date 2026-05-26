"""
AlgoTrader — Main FastAPI Application
Run with: python main.py  (or: uvicorn main:app --port 5000)
"""
import os
import sys
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from storage.csv_store import init_all_csvs
from data_sources.option_chain_service import start_service
from config import OPTION_CHAIN_REFRESH_SECONDS
from api.routes_dashboard import router as dashboard_router
from api.routes_algo import router as algo_router
from api.routes_backtest import router as backtest_router
from api.routes_calendar import router as calendar_router
from api.routes_paper import router as paper_router
from api.routes_logs import router as logs_router
from api.routes_option_chain import router as option_chain_router
from api.routes_settings import router as settings_router
from data_sources.dhan_fetcher import get_dhan_fetcher
from utils.settings_store import get_dhan_token

# ── Init ───────────────────────────────────────────────────────────────────────
init_all_csvs()

# Start background option chain polling service (NSE live data)
option_chain_svc = start_service(refresh_seconds=OPTION_CHAIN_REFRESH_SECONDS)

# Sync Dhan token from settings on startup
dhan_fetcher = get_dhan_fetcher()
dhan_fetcher.set_auth_token(get_dhan_token())

app = FastAPI(
    title="AlgoTrader",
    description="Unified NIFTY50 Algo Trading Dashboard",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API routes ─────────────────────────────────────────────────────────────────
app.include_router(dashboard_router)
app.include_router(algo_router)
app.include_router(backtest_router)
app.include_router(calendar_router)
app.include_router(paper_router)
app.include_router(logs_router)
app.include_router(option_chain_router)
app.include_router(settings_router)

# ── Static files ───────────────────────────────────────────────────────────────
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")
STATIC_DIR   = os.path.join(FRONTEND_DIR, "static")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ── HTML page routes ───────────────────────────────────────────────────────────
@app.get("/", response_class=FileResponse)
def index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/algo/{algo_id}", response_class=FileResponse)
def algo_detail(algo_id: str):
    return FileResponse(os.path.join(FRONTEND_DIR, "algo_detail.html"))


@app.get("/logs.html", response_class=FileResponse)
def logs_page():
    return FileResponse(os.path.join(FRONTEND_DIR, "logs.html"))


@app.get("/settings.html", response_class=FileResponse)
def settings_page():
    return FileResponse(os.path.join(FRONTEND_DIR, "settings.html"))


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8888, reload=True)
