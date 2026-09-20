from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import os

from app.database import init_db
from app.routes import auth, cases, dashboard, reports, transactions


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="BankGuard AI Fraud Detection API",
    description="Fraud detection dashboard API for transaction monitoring and case management.",
    version="1.0.0",
    lifespan=lifespan,
)

# Dozwolone źródła były wpisane na sztywno jako porty deweloperskie Vite, więc
# każde uruchomienie frontendu pod innym adresem — inny port, podgląd builda,
# wdrożenie — kończyło się zablokowaniem logowania przez CORS i wymagało zmiany
# w kodzie. Lista pochodzi teraz ze zmiennej środowiskowej, a domyślne wartości
# są te same co wcześniej, więc dotychczasowy sposób pracy działa bez zmian.
DEFAULT_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("BANKGUARD_CORS_ORIGINS", DEFAULT_CORS_ORIGINS).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(cases.router)
app.include_router(dashboard.router)
app.include_router(reports.router)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "bankguard-ai-api"}

