import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
import models  # noqa: F401 — import registers all ORM models with SQLAlchemy
from routers import auth_router, applications_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Job Application Co-Pilot API",
    description="AI-powered multi-agent job application assistant",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ALLOWED_ORIGINS env var: comma-separated list of frontend origins.
# Example: "https://your-app.onrender.com,https://your-app.netlify.app"
# Defaults to "*" for local dev — always set explicitly in production.
_raw_origins = os.getenv("ALLOWED_ORIGINS", "*")
allowed_origins = [o.strip() for o in _raw_origins.split(",")] if _raw_origins != "*" else ["*"]
print(f"Loaded ALLOWED_ORIGINS={allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(applications_router.router)


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "docs": "/docs"}