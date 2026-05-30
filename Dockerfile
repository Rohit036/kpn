FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# COPY data/vector_store /app/data/vector_store
COPY src /app/src
COPY scripts /app/scripts
COPY README.md /app/README.md

EXPOSE 8000

# Use shell form so the container can respect the PORT env var provided by PaaS
CMD ["sh", "-c", "python scripts/run_api.py --host 0.0.0.0 --port ${PORT:-8000}"]
