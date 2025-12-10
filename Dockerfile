FROM python:3.12-slim
LABEL authors="vertig0"

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libgl1 \
    libxrender1 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

RUN python -c "import easyocr; easyocr.Reader(['en','pl'], model_storage_directory='/app/resources/models')"

COPY src/ /app/src/

WORKDIR src

EXPOSE 8501

CMD ["streamlit", "run", "web.py"]