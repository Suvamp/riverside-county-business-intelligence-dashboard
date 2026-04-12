FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libexpat1 \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 7860

CMD ["gunicorn", "app:server", "--workers", "1", "--threads", "2", "--timeout", "300", "--bind", "0.0.0.0:7860"]
