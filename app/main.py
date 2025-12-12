from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import shutil
from pathlib import Path
import logging

from app.core.config import settings
from app.api.endpoints import ocr

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    Handles startup and shutdown events
    """
    # Startup: Clean and create temp directory
    logger.info("Starting up OCR API...")
    temp_dir = Path(settings.TEMP_DIR)

    if temp_dir.exists():
        logger.info(f"Cleaning existing temp directory: {temp_dir}")
        shutil.rmtree(temp_dir, ignore_errors=True)

    temp_dir.mkdir(exist_ok=True)
    logger.info(f"Temp directory created: {temp_dir}")

    yield

    # Shutdown: Clean temp directory
    logger.info("Shutting down OCR API...")
    if temp_dir.exists():
        logger.info(f"Cleaning temp directory: {temp_dir}")
        shutil.rmtree(temp_dir, ignore_errors=True)


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="API for extracting text from images using OCR. Supports archive files and direct image uploads.",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    ocr.router,
    prefix="/api/v1/ocr",
    tags=["OCR"]
)


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "running",
        "docs": "/docs",
        "ocr_endpoint": "/api/v1/ocr/extract"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.VERSION
    }
