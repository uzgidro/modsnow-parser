from pydantic_settings import BaseSettings
from typing import List
import json


class Settings(BaseSettings):
    """Application configuration settings"""

    # Application
    APP_NAME: str = "OCR Image Processing API"
    VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # File Processing
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB
    MAX_ARCHIVE_SIZE: int = 500 * 1024 * 1024  # 500MB
    MAX_IMAGES_PER_REQUEST: int = 50
    TEMP_DIR: str = "./temp"

    # OCR Settings
    OCR_LANGUAGES: str = '["en"]'  # JSON string
    OCR_GPU_ENABLED: bool = False
    OCR_TIMEOUT_SECONDS: int = 30
    MAX_CONCURRENT_OCR: int = 4

    # OCR Cleanup Options
    OCR_PARAGRAPH_MODE: bool = False  # Merge lines into paragraphs
    OCR_MIN_CONFIDENCE: float = 0.0  # Filter out low-confidence text (0.0 - 1.0)
    OCR_STRIP_WHITESPACE: bool = True  # Remove leading/trailing whitespace
    OCR_REMOVE_EMPTY_LINES: bool = False  # Remove empty lines from output

    # OCR Performance Options
    OCR_MAX_IMAGE_SIZE: int = 1920  # Resize images larger than this (width in pixels, 0 = no resize)
    OCR_BATCH_SIZE: int = 5  # EasyOCR batch processing size

    # Supported Formats
    SUPPORTED_ARCHIVE_FORMATS: List[str] = ["zip", "rar", "7z", "tar", "gz", "bz2"]
    SUPPORTED_IMAGE_FORMATS: List[str] = ["png", "jpg", "jpeg"]

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def ocr_languages_list(self) -> List[str]:
        """Parse OCR_LANGUAGES from JSON string"""
        try:
            return json.loads(self.OCR_LANGUAGES)
        except (json.JSONDecodeError, TypeError):
            return ["en"]


settings = Settings()
