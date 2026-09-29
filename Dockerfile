FROM python:3.12-slim AS builder

#---------Build stage---------
WORKDIR /usr/src/app

# Install dependencies first to make better use of Docker's build cache.
COPY requirements.txt ./
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY app/app.py ./app/app.py
COPY config/logging_config.py ./config/logging_config.py
COPY models/ ./models/
COPY services/mask_image.py ./services/mask_image.py
COPY utils/encrypt_decrypt.py ./utils/encrypt_decrypt.py
COPY wsgi.py ./

#---------Final stage---------
# FROM python:3.12-slim
# WORKDIR /usr/src/app

# COPY --from=builder /usr/src/app/ ./

ENV secret_key="Navjyot!"
ENV password="Masking@101"

CMD ["python", "wsgi.py"]
