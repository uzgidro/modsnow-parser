from fastapi import APIRouter, UploadFile, File, HTTPException, status
from typing import List, Optional
import time
from pathlib import Path
import shutil
import uuid
import aiofiles
import logging
from contextlib import asynccontextmanager

from app.models.responses import OCRResponse, ImageResult, ImageError
from app.services.archive_service import ArchiveService
from app.services.image_service import ImageService
from app.services.ocr_service import OCRService
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services (singleton pattern)
archive_service = ArchiveService(temp_base_dir=settings.TEMP_DIR)
image_service = ImageService()
ocr_service = OCRService(
    languages=settings.ocr_languages_list,
    gpu=settings.OCR_GPU_ENABLED,
    max_workers=settings.MAX_CONCURRENT_OCR
)


@asynccontextmanager
async def temporary_directory(base_dir: Path):
    """
    Context manager for temporary directory with guaranteed cleanup
    """
    temp_dir = base_dir / f"temp_{uuid.uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        yield temp_dir
    finally:
        # Always cleanup, even on exception
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
            logger.debug(f"Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            logger.error(f"Failed to cleanup {temp_dir}: {e}")


@router.post("/extract", response_model=OCRResponse)
async def extract_text_from_files(
    archive: Optional[UploadFile] = File(None),
    images: Optional[List[UploadFile]] = File(None)
):
    """
    Extract text from images using OCR

    Accepts either:
    - Single archive file (ZIP, RAR, 7Z, TAR)
    - Multiple image files (PNG, JPEG)

    Returns:
        OCRResponse with extracted text and metadata
    """
    start_time = time.time()

    # Validate input
    if not archive and not images:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'archive' or 'images' must be provided"
        )

    if archive and images:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either 'archive' OR 'images', not both"
        )

    image_paths = []
    relative_base = None

    try:
        async with temporary_directory(Path(settings.TEMP_DIR)) as temp_dir:

            if archive:
                # Process archive
                logger.info(f"Processing archive: {archive.filename}")

                # Validate archive format
                if not archive_service.is_supported_archive(archive.filename):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Unsupported archive format. Supported: {', '.join(settings.SUPPORTED_ARCHIVE_FORMATS)}"
                    )

                try:
                    extract_dir = await archive_service.extract_archive(archive)
                    image_paths = image_service.find_images_recursive(extract_dir)
                    relative_base = extract_dir
                except Exception as e:
                    logger.error(f"Archive extraction failed: {e}")
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Failed to extract archive: {str(e)}"
                    )

            else:
                # Process uploaded images
                logger.info(f"Processing {len(images)} uploaded images")

                for img_file in images:
                    # Validate image
                    if not await image_service.validate_uploaded_image(img_file):
                        logger.warning(f"Skipping invalid image: {img_file.filename}")
                        continue

                    # Save to temp
                    img_path = temp_dir / img_file.filename
                    async with aiofiles.open(img_path, 'wb') as f:
                        content = await img_file.read()
                        await f.write(content)

                    image_paths.append(img_path)

                relative_base = temp_dir

            # Check if any images were found
            if not image_paths:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No valid PNG or JPEG images found"
                )

            # Check image count limit
            if len(image_paths) > settings.MAX_IMAGES_PER_REQUEST:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Too many images. Maximum: {settings.MAX_IMAGES_PER_REQUEST}, Found: {len(image_paths)}"
                )

            logger.info(f"Found {len(image_paths)} images to process")

            # Process images with OCR
            results, errors = await ocr_service.batch_process_images(
                image_paths,
                relative_to=relative_base
            )

            # Calculate response
            processing_time = time.time() - start_time
            total_images = len(image_paths)
            processed_images = len(results)

            response_status = "success" if not errors else "partial_success"

            # Convert results to response models
            image_results = [
                ImageResult(
                    filename=r['filename'],
                    text=r['text'],
                    confidence=round(r['confidence'], 4),
                    language=settings.ocr_languages_list[0]  # Use first language
                )
                for r in results
            ]

            image_errors = [
                ImageError(filename=e['filename'], error=e['error'])
                for e in errors
            ] if errors else None

            return OCRResponse(
                status=response_status,
                total_images=total_images,
                processed_images=processed_images,
                results=image_results,
                errors=image_errors,
                processing_time_seconds=round(processing_time, 2)
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OCR processing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Processing failed: {str(e)}"
        )
