import easyocr
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
import numpy as np
import cv2

logger = logging.getLogger(__name__)


class OCRService:
    """Service for extracting text from images using EasyOCR"""

    def __init__(
        self,
        languages: List[str] = ['en'],
        gpu: bool = False,
        max_workers: int = 4,
        paragraph_mode: bool = False,
        min_confidence: float = 0.0,
        strip_whitespace: bool = True,
        remove_empty_lines: bool = False,
        max_image_size: int = 1920
    ):
        """
        Initialize EasyOCR reader

        Args:
            languages: List of language codes (e.g., ['en', 'ru', 'zh'])
            gpu: Use GPU acceleration if available
            max_workers: Maximum number of concurrent OCR operations
            paragraph_mode: Merge lines into paragraphs with spaces
            min_confidence: Minimum confidence threshold (0.0 - 1.0)
            strip_whitespace: Remove leading/trailing whitespace from text
            remove_empty_lines: Remove empty lines from output
            max_image_size: Maximum image width in pixels (resize if larger, 0 = no resize)
        """
        logger.info(f"Initializing EasyOCR with languages: {languages}, GPU: {gpu}")
        self.reader = easyocr.Reader(
            languages,
            gpu=gpu,
            verbose=False
        )
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.max_concurrent = max_workers
        self.min_confidence = min_confidence
        self.strip_whitespace = strip_whitespace
        self.remove_empty_lines = remove_empty_lines
        self.paragraph_mode = paragraph_mode
        self.max_image_size = max_image_size

    async def extract_text_from_image(self, image_path: Path) -> Dict:
        """
        Extract text from single image asynchronously

        Args:
            image_path: Path to image file

        Returns:
            Dictionary with keys:
                - text: Extracted text as string
                - confidence: Average confidence score
                - details: Detailed results with bounding boxes
        """
        loop = asyncio.get_event_loop()

        try:
            # Run OCR in thread pool (CPU-intensive operation)
            result = await loop.run_in_executor(
                self.executor,
                self._process_image,
                str(image_path)
            )

            # Parse results
            if result:
                # Filter by confidence threshold
                if self.min_confidence > 0:
                    result = [r for r in result if r[2] >= self.min_confidence]

                if not result:
                    return {
                        'text': '',
                        'confidence': 0.0,
                        'details': []
                    }

                # Extract text and apply cleanup
                text_lines = [detection[1] for detection in result]

                # Apply whitespace stripping
                if self.strip_whitespace:
                    text_lines = [line.strip() for line in text_lines]

                # Remove empty lines if requested
                if self.remove_empty_lines:
                    text_lines = [line for line in text_lines if line]

                # Combine text
                if self.paragraph_mode:
                    # Join with spaces for paragraph mode
                    text = ' '.join(text_lines)
                else:
                    # Join with newlines for line mode
                    text = '\n'.join(text_lines)

                # Calculate average confidence
                confidences = [detection[2] for detection in result]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

                return {
                    'text': text,
                    'confidence': avg_confidence,
                    'details': result
                }
            else:
                return {
                    'text': '',
                    'confidence': 0.0,
                    'details': []
                }

        except Exception as e:
            raise Exception(f"OCR processing failed: {str(e)}")

    def _process_image(self, image_path: str) -> List:
        """
        Synchronous OCR processing
        Uses cv2.imdecode to support Unicode file paths

        Args:
            image_path: Path to image as string

        Returns:
            List of detection results
        """
        # Read image using numpy to handle Unicode paths
        # cv2.imread() fails with non-ASCII characters in path on Windows
        with open(image_path, 'rb') as f:
            image_data = np.frombuffer(f.read(), np.uint8)

        # Decode image from buffer
        image = cv2.imdecode(image_data, cv2.IMREAD_COLOR)

        if image is None:
            raise ValueError(f"Failed to decode image: {image_path}")

        # Resize image if too large (speeds up OCR significantly)
        if self.max_image_size > 0:
            height, width = image.shape[:2]
            if width > self.max_image_size:
                scale = self.max_image_size / width
                new_width = self.max_image_size
                new_height = int(height * scale)
                image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
                logger.debug(f"Resized image from {width}x{height} to {new_width}x{new_height}")

        # Pass numpy array to EasyOCR instead of file path
        return self.reader.readtext(image)

    async def batch_process_images(
        self,
        image_paths: List[Path],
        relative_to: Optional[Path] = None
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Process multiple images concurrently

        Args:
            image_paths: List of paths to image files
            relative_to: Base path for calculating relative filenames

        Returns:
            Tuple of (results, errors)
                - results: List of successful processing results
                - errors: List of error dictionaries
        """
        tasks = []

        for image_path in image_paths:
            tasks.append(self._process_single_with_filename(image_path, relative_to))

        # Process with semaphore to limit concurrency
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def bounded_task(task):
            async with semaphore:
                return await task

        logger.info(f"Processing {len(tasks)} images with max concurrency {self.max_concurrent}")

        results = await asyncio.gather(
            *[bounded_task(task) for task in tasks],
            return_exceptions=True
        )

        # Separate successes and failures
        processed_results = []
        errors = []

        for result in results:
            if isinstance(result, Exception):
                errors.append({
                    'filename': 'unknown',
                    'error': str(result)
                })
            elif result.get('error'):
                errors.append(result)
            else:
                processed_results.append(result)

        logger.info(f"Processed {len(processed_results)} images successfully, {len(errors)} errors")

        return processed_results, errors

    async def _process_single_with_filename(
        self,
        image_path: Path,
        relative_to: Optional[Path] = None
    ) -> Dict:
        """
        Process single image and return with filename

        Args:
            image_path: Path to image file
            relative_to: Base path for calculating relative filename

        Returns:
            Dictionary with filename, text, confidence, and optionally error
        """
        try:
            result = await self.extract_text_from_image(image_path)

            # Calculate relative filename for better presentation
            if relative_to:
                try:
                    filename = str(image_path.relative_to(relative_to))
                except ValueError:
                    filename = image_path.name
            else:
                filename = image_path.name

            return {
                'filename': filename,
                'text': result['text'],
                'confidence': result['confidence']
            }

        except Exception as e:
            logger.error(f"Failed to process {image_path.name}: {e}")
            return {
                'filename': str(image_path.name),
                'error': str(e)
            }
