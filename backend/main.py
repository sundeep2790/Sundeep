import os
import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from datarescue.backend.database import engine, Base
from datarescue.backend.routes import credits, licence
from datarescue.backend import stripe_webhooks

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("datarescue")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup database table creation
    logger.info("Initializing database tables on startup...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized successfully.")
    yield
    # Shutdown logic can go here

app = FastAPI(
    title="DataRescue API",
    version="1.0.0",
    description="Backend service for DataRescue credit management and licence validation.",
    lifespan=lifespan
)

# CORS middleware to support desktop app and browser calls.
# Origins are read from the CORS_ORIGINS env var (comma-separated).
# Default: localhost only. Do NOT use wildcard ("*") with allow_credentials=True.
_raw_origins = os.getenv("CORS_ORIGINS", "http://localhost:8000,http://localhost:3000")
_allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["X-Device-Token", "X-User-Email", "Content-Type", "Stripe-Signature"],
)

# Request timing logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    logger.info(
        f"API Request: {request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Duration: {duration:.4f}s"
    )
    return response

app.include_router(credits.router)
app.include_router(licence.router)
app.include_router(stripe_webhooks.router)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
