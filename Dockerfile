FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 HOST=0.0.0.0 PORT=5000

RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr libglib2.0-0 && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

# CPU-only torch (saves ~3-4 GB)
RUN pip install torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN grep -viE '^(uuid|ninja|opencv-python)==' requirements.txt \
    && pip install -r requirements.txt \
    && pip uninstall -y opencv-python opencv-python-headless \
    && pip install opencv-python-headless==4.11.0.86 \
    && rm requirements.txt

COPY app/app.py ./app/app.py
COPY services/mask_image.py ./services/mask_image.py
COPY services/encrypt_decrypt.py ./services/encrypt_decrypt.py
COPY models/ ./models/
COPY wsgi.py .

EXPOSE 5000
CMD ["python", "wsgi.py"]

