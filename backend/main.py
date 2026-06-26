from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
import models  # noqa: F401 — import registers all ORM models with SQLAlchemy
from routers import auth_router, applications_router

# Creates all tables defined in models.py on startup.
# Safe to run every time — only creates tables that don't exist yet.
# For schema CHANGES after first run, use Alembic migrations instead.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Job Application Co-Pilot API",
    description="AI-powered multi-agent job application assistant",
    version="1.0.0",
    docs_url="/docs",    # Swagger UI: http://localhost:8000/docs
    redoc_url="/redoc",  # ReDoc:      http://localhost:8000/redoc
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # Replace with your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(applications_router.router)


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "docs": "/docs"}