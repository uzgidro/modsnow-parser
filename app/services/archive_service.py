from pathlib import Path
from fastapi import UploadFile
import zipfile
import tarfile
import rarfile
import shutil
import uuid
import aiofiles
import logging

# Try to import py7zr (optional dependency)
try:
    import py7zr
    PY7ZR_AVAILABLE = True
except ImportError:
    PY7ZR_AVAILABLE = False

logger = logging.getLogger(__name__)


class ArchiveService:
    """Service for extracting archive files"""

    def __init__(self, temp_base_dir: str = "./temp"):
        self.temp_base_dir = Path(temp_base_dir)
        self.temp_base_dir.mkdir(exist_ok=True)

        # Build supported archives based on available libraries
        self.SUPPORTED_ARCHIVES = {
            'zip': 'zipfile',
            'rar': 'rarfile',
            'tar': 'tarfile',
            'gz': 'tarfile',
            'bz2': 'tarfile'
        }

        # Configure rarfile to use system unrar
        rarfile.UNRAR_TOOL = "unrar"

        if PY7ZR_AVAILABLE:
            self.SUPPORTED_ARCHIVES['7z'] = 'py7zr'
        else:
            logger.warning("py7zr not available - 7z archives will not be supported")

    async def extract_archive(self, file: UploadFile) -> Path:
        """
        Extract archive to temporary directory

        Args:
            file: Uploaded archive file

        Returns:
            Path to extraction directory

        Raises:
            ValueError: If archive format is unsupported
            Exception: If extraction fails
        """
        # Create unique temp directory for this extraction
        extract_dir = self.temp_base_dir / f"extract_{uuid.uuid4().hex}"
        extract_dir.mkdir(parents=True, exist_ok=True)

        # Save uploaded file temporarily
        archive_path = extract_dir / file.filename

        try:
            # Write uploaded file
            async with aiofiles.open(archive_path, 'wb') as f:
                content = await file.read()
                await f.write(content)

            logger.info(f"Extracting archive: {file.filename}")

            # Detect archive type and extract
            extension = self._get_extension(file.filename)

            if extension == 'zip':
                self._extract_zip(archive_path, extract_dir)

            elif extension in ['tar', 'gz', 'bz2']:
                self._extract_tar(archive_path, extract_dir)

            elif extension == '7z':
                self._extract_7z(archive_path, extract_dir)

            elif extension == 'rar':
                self._extract_rar(archive_path, extract_dir)

            else:
                raise ValueError(f"Unsupported archive format: {extension}")

            # Remove archive file after extraction
            archive_path.unlink()

            logger.info(f"Archive extracted successfully to {extract_dir}")
            return extract_dir

        except Exception as e:
            # Cleanup on failure
            logger.error(f"Archive extraction failed: {e}")
            shutil.rmtree(extract_dir, ignore_errors=True)
            raise

    def _get_extension(self, filename: str) -> str:
        """Get file extension, handling .tar.gz and .tar.bz2"""
        filename_lower = filename.lower()

        if filename_lower.endswith('.tar.gz') or filename_lower.endswith('.tgz'):
            return 'gz'
        elif filename_lower.endswith('.tar.bz2'):
            return 'bz2'
        else:
            return Path(filename).suffix[1:].lower()  # Remove leading dot

    def _extract_zip(self, archive_path: Path, extract_dir: Path):
        """Extract ZIP archive"""
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

    def _extract_tar(self, archive_path: Path, extract_dir: Path):
        """Extract TAR archive (including .tar.gz, .tar.bz2)"""
        with tarfile.open(archive_path, 'r:*') as tar_ref:
            tar_ref.extractall(extract_dir)

    def _extract_7z(self, archive_path: Path, extract_dir: Path):
        """Extract 7Z archive"""
        if not PY7ZR_AVAILABLE:
            raise ImportError("py7zr library is not available. Install it with: pip install py7zr")
        with py7zr.SevenZipFile(archive_path, 'r') as sz_ref:
            sz_ref.extractall(extract_dir)

    def _extract_rar(self, archive_path: Path, extract_dir: Path):
        """Extract RAR archive"""
        with rarfile.RarFile(archive_path, 'r') as rar_ref:
            rar_ref.extractall(extract_dir)

    def is_supported_archive(self, filename: str) -> bool:
        """Check if file is a supported archive format"""
        extension = self._get_extension(filename)
        return extension in self.SUPPORTED_ARCHIVES
