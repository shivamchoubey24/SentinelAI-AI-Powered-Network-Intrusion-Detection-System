FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

WORKDIR /app

# CPU-only TensorFlow keeps the image far smaller than the GPU build.
COPY requirements.txt .
RUN sed 's/^tensorflow>=/tensorflow-cpu>=/' requirements.txt > /tmp/req.txt \
    && pip install -r /tmp/req.txt

COPY src ./src
COPY scripts ./scripts
COPY config ./config
COPY docker-entrypoint.sh ./docker-entrypoint.sh

# Run as an unprivileged user; data/ and logs/ are the only writable paths.
RUN useradd --create-home --uid 10001 sentinel \
    && mkdir -p data/models data/blockchain data/processed logs \
    && chmod +x docker-entrypoint.sh \
    && chown -R sentinel:sentinel /app
USER sentinel

ENV API_HOST=0.0.0.0 API_PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request,os;urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"API_PORT\",\"8000\")}/health',timeout=4)"

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["python", "-m", "src.api.main"]
