from pydantic import BaseModel
from typing import List, Optional


class ImageResult(BaseModel):
    """Result of OCR processing for a single image"""
    filename: str
    text: str
    confidence: float
    language: str = "en"


class ImageError(BaseModel):
    """Error encountered while processing an image"""
    filename: str
    error: str


class OCRResponse(BaseModel):
    """Response model for OCR extraction endpoint"""
    status: str  # "success" | "partial_success"
    total_images: int
    processed_images: int
    results: List[ImageResult]
    errors: Optional[List[ImageError]] = None
    processing_time_seconds: float
