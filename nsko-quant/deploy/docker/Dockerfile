# NSKO QUANT engine, optional "advanced server" route (for example a small always-on Linux box).
# Build from nsko-quant/engine:   docker build -f ../deploy/docker/Dockerfile -t nsko-quant-engine .
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 NSQ_DATA=/data NSQ_VAULT_BACKEND=file
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY nsq ./nsq
RUN useradd -m -u 10001 nsq && mkdir -p /data && chown nsq /data
USER nsq
VOLUME ["/data"]
EXPOSE 8787
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8787/health',timeout=4)"
# 0.0.0.0 inside the container only; compose publishes it on the host's 127.0.0.1.
CMD ["python", "-m", "nsq", "--host", "0.0.0.0"]
