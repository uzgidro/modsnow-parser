from pathlib import Path
from typing import List
from fastapi import UploadFile
from PIL import Image
import io
import logging

logger = logging.getLogger(__name__)


class ImageService:
    """Service for finding and validating image files"""

    SUPPORTED_EXTENSIONS = {'.png', '.jpg', '.jpeg'}

    def find_images_recursive(self, root_dir: Path) -> List[Path]:
        """
        Recursively find all PNG and JPEG images in directory

        Args:
            root_dir: Root directory to search

        Returns:
            List of paths to valid image files
        """
        images = []

        for item in root_dir.rglob('*'):
            if item.is_file():
                if item.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                    # Validate it's actually an image
                    if self.is_valid_image(item):
                        images.append(item)
                    else:
                        logger.warning(f"Skipping invalid image file: {item}")

        return images

    def is_valid_image(self, path: Path) -> bool:
        """
        Validate that file is a valid readable image

        Args:
            path: Path to image file

        Returns:
            True if valid image, False otherwise
        """
        try:
            img = Image.open(path)
            img.verify()
            return True
        except Exception as e:
            logger.debug(f"Image validation failed for {path}: {e}")
            return False

    async def validate_uploaded_image(self, file: UploadFile) -> bool:
        """
        Validate uploaded file is a valid image

        Args:
            file: Uploaded file to validate

        Returns:
            True if valid image, False otherwise
        """
        # Check content type
        if file.content_type and not file.content_type.startswith('image/'):
            logger.debug(f"Invalid content type: {file.content_type}")
            return False

        # Check extension
        extension = Path(file.filename).suffix.lower()
        if extension not in self.SUPPORTED_EXTENSIONS:
            logger.debug(f"Unsupported extension: {extension}")
            return False

        # Validate with PIL
        try:
            content = await file.read()
            await file.seek(0)  # Reset for later reading

            img = Image.open(io.BytesIO(content))
            img.verify()
            return True
        except Exception as e:
            logger.debug(f"Image validation failed for {file.filename}: {e}")
            return False
