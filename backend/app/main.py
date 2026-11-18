import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base
# Explicitly import models so SQLAlchemy metadata registers them prior to table creation
from app.models import user, organization, plan
from app.api import auth_router, agent_router, document_router, plan_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure all tables exist on startup
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"Warning: Database initialization error: {e}")
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Multi-tenant Autonomous Marketing Planner SaaS Backend",
    version="1.0.0",
    lifespan=lifespan
)

# Parse allowed origins safely from config
frontend_origins = [
    origin.strip()
    for origin in settings.FRONTEND_URL.split(",")
    if origin.strip()
]
if not frontend_origins:
    frontend_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all API routers with their standardized /api/v1 prefixes
app.include_router(auth_router.router)
app.include_router(agent_router.router)
app.include_router(document_router.router)
app.include_router(plan_router.router)

@app.get("/")
def health_check():
    return {
        "status": "ok",
        "app": settings.PROJECT_NAME,
        "message": "MarketPilot AI Backend is running smoothly."
    }

@app.get("/health")
def status_health():
    return {"status": "healthy"}