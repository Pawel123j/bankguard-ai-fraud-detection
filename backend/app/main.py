from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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

