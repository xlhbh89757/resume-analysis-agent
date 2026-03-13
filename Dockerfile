FROM python:3.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    LIBREOFFICE_PATH=/usr/bin/soffice

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice \
    libreoffice-writer \
    fonts-noto-cjk \
    fonts-dejavu-core \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY . /app

RUN python -m pip install --upgrade pip && \
    python -m pip install \
    fastapi \
    "uvicorn[standard]" \
    sqlalchemy \
    alembic \
    pydantic \
    pydantic-settings \
    celery \
    redis \
    pymysql \
    PyPDF2 \
    pymupdf \
    pdfplumber \
    python-docx \
    pillow \
    rapidocr-onnxruntime \
    qdrant-client \
    fastembed \
    pyyaml \
    python-multipart \
    aiofiles \
    httpx \
    openai \
    anthropic

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
