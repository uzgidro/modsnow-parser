# OCR Image Processing API

FastAPI-based REST API for extracting text from images using EasyOCR.

## Features

- Extract text from images (PNG, JPEG)
- Process multiple images from archives (ZIP, TAR, GZ, BZ2)
- Batch processing with concurrency control
- Confidence scores for extracted text
- Docker-ready deployment

## Supported Formats

**Images:** PNG, JPEG, JPG
**Archives:** ZIP, RAR, TAR, TAR.GZ, TAR.BZ2

## Quick Start

### Local Development

1. **Install UnRAR (for RAR support):**

**Windows:**
```bash
# Option 1: winget
winget install RARLab.WinRAR

# Option 2: Chocolatey
choco install winrar

# Option 3: Download from https://www.rarlab.com/rar_add.htm
```

**Linux/macOS:**
```bash
# Ubuntu/Debian
sudo apt-get install unrar

# macOS
brew install unrar
```

2. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure environment:**
```bash
cp .env.example .env
# Edit .env as needed
```

4. **Run the server:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

5. **Access the API:**
- API: http://localhost:8000
- Documentation: http://localhost:8000/docs

### Docker Deployment

1. **Build and run with Docker Compose:**
```bash
docker-compose up -d
```

2. **Or build manually:**
```bash
# Build image
docker build -t ocr-api .

# Run container
docker run -d \
  -p 8000:8000 \
  -e OCR_LANGUAGES=en \
  -e OCR_GPU=false \
  --name ocr-api \
  ocr-api
```

3. **Check logs:**
```bash
docker-compose logs -f
```

4. **Stop:**
```bash
docker-compose down
```

## API Usage

### Extract Text from Images

**Endpoint:** `POST /api/v1/ocr/extract`

**Option 1 - Upload Archive:**
```bash
curl -X POST "http://localhost:8000/api/v1/ocr/extract" \
  -F "archive=@images.zip"
```

**Option 2 - Upload Images Directly:**
```bash
curl -X POST "http://localhost:8000/api/v1/ocr/extract" \
  -F "images=@image1.png" \
  -F "images=@image2.jpg"
```

**Response:**
```json
{
  "status": "success",
  "total_images": 2,
  "successful": 2,
  "failed": 0,
  "processing_time": 1.23,
  "results": [
    {
      "filename": "image1.png",
      "text": "Extracted text here",
      "confidence": 0.95
    }
  ],
  "errors": []
}
```

## Configuration

Edit `.env` file or set environment variables:

```bash
# OCR Settings
OCR_GPU_ENABLED=False          # Enable GPU acceleration
OCR_LANGUAGES=["en"]           # OCR languages (en, ch_sim, etc.)
MAX_CONCURRENT_OCR=4           # Max concurrent OCR operations

# File Limits
MAX_UPLOAD_SIZE=104857600      # Max upload size (100MB)
MAX_ARCHIVE_SIZE=524288000     # Max archive size (500MB)
MAX_IMAGES_PER_REQUEST=50      # Max images per request
TEMP_DIR=./temp                # Temporary file directory
```

## Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  FastAPI    │  POST /api/v1/ocr/extract
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Archive   │  Extract ZIP/TAR
│   Service   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Image     │  Validate images
│   Service   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│     OCR     │  Extract text (EasyOCR)
│   Service   │  Batch processing
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Response  │  JSON with results
└─────────────┘
```

## Tech Stack

- **FastAPI** - Web framework
- **EasyOCR** - OCR engine
- **PyTorch** - Deep learning backend
- **Uvicorn** - ASGI server
- **Pydantic** - Data validation

## Development

**Project Structure:**
```
modsnow/
├── app/
│   ├── main.py              # Application entry point
│   ├── api/
│   │   └── endpoints/
│   │       └── ocr.py       # OCR endpoint
│   ├── services/
│   │   ├── ocr_service.py   # OCR processing
│   │   ├── archive_service.py
│   │   └── image_service.py
│   ├── models/
│   │   └── responses.py     # Response models
│   └── core/
│       └── config.py        # Configuration
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env
```

## License

MIT
