FROM python:3.12-slim

WORKDIR /app

# Dependencias del sistema
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev \
    gcc \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código y modelo
COPY src/ ./src/
COPY models/ ./models/

# Variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src
ENV TZ=America/Bogota

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')"

CMD ["uvicorn", "futuisp_analytics.interfaces.api.main:app", "--host", "0.0.0.0", "--port", "8000"]