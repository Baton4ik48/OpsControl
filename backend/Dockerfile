FROM python:3.11-slim-bookworm@sha256:d29f48a31a8b408ed19272ca1e7b10ebae13b240a27e862d3d4217c528e2e0c3

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
 && pip install --no-cache-dir -r requirements.txt \
 && rm -f /usr/local/lib/python3.11/site-packages/pip/_vendor/bom.cdx.json

COPY . .

RUN useradd --create-home --uid 10001 appuser \
 && mkdir -p /app/logs \
 && chown -R appuser:appuser /app
USER appuser

EXPOSE 9000
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

