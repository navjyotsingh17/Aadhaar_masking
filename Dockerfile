FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 HOST=0.0.0.0 PORT=5000

RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr poppler-utils libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

# CPU-only torch (saves ~3-4 GB)
RUN pip install torch==2.6.0 torchvision==0.21.0 \
    --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN grep -viE '^(uuid|ninja|opencv-python)==' requirements.txt > req.txt \
    && pip install -r req.txt \
    && pip uninstall -y opencv-python opencv-python-headless \
    && pip install opencv-python-headless==4.11.0.86 \
    && rm req.txt

COPY app/ ./app/
COPY config/ ./config/
COPY services/ ./services/
COPY utils/ ./utils/
COPY models/ ./models/
COPY wsgi.py .

EXPOSE 5000
CMD ["python", "wsgi.py"]