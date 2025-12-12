import easyocr
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging

logger = logging.getLogger(__name__)


class OCRService:
    """Service for extracting text from images using EasyOCR"""

    def __init__(self, languages: List[str] = ['en'], gpu: bool = False, max_workers: int = 4):
        """
        Initialize EasyOCR reader

        Args:
            languages: List of language codes (e.g., ['en', 'ru', 'zh'])
            gpu: Use GPU acceleration if available
            max_workers: Maximum number of concurrent OCR operations
        """
        logger.info(f"Initializing EasyOCR with languages: {languages}, GPU: {gpu}")
        self.reader = easyocr.Reader(
            languages,
            gpu=gpu,
            verbose=False
        )
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.max_concurrent = max_workers

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
                # Combine all text with newlines
                text = '\n'.join([detection[1] for detection in result])

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

        Args:
            image_path: Path to image as string

        Returns:
            List of detection results
        """
        return self.reader.readtext(image_path)

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
