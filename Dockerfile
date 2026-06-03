FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scripts ./scripts
COPY docs ./docs

ENV PROXY_HOST=0.0.0.0 \
    PROXY_PORT=9890 \
    IMAGE_PROXY_STATE_DIR=/data \
    PUBLIC_BASE_URL=http://localhost:9890

RUN mkdir -p /data/generated

EXPOSE 9890

CMD ["python3", "scripts/proxy.py"]
