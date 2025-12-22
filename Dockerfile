FROM python:3.14.2-slim
LABEL authors="vertig0"

RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    libgl1 \
    libglib2.0-0 \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    zlib1g-dev \
    libopenblas-dev \
    gfortran \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

WORKDIR /app

RUN pip install --no-cache-dir \
    torch torchvision \
    --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN python -c "import easyocr; easyocr.Reader(['pl'], gpu=False, model_storage_directory='/app/resources/models')"

COPY src/ /app/src/

WORKDIR src

EXPOSE 8501

CMD ["streamlit", "run", "web.py"]