### ===== BUILDER =====
FROM python:3.14.2-slim AS builder

RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    gfortran \
    pkg-config \
    libopenblas-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip setuptools wheel

WORKDIR /install

COPY requirements.txt .

RUN pip install --no-cache-dir \
    torch torchvision \
    --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

RUN python - <<EOF
import easyocr
easyocr.Reader(['pl'], gpu=False, model_storage_directory='/install/models')
EOF


### ===== RUNTIME =====
FROM python:3.14.2-slim

RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libopenblas0 \
    libjpeg62-turbo \
    libpng16-16 \
    libtiff6 \
    zlib1g \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.14 /usr/local/lib/python3.14
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /install/models /app/resources/models

COPY src/ /app/src/

WORKDIR /app/src

EXPOSE 8501

CMD ["streamlit", "run", "web.py"]