FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .

RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-noto-cjk xvfb \
    && pip install --no-cache-dir -r requirements.txt \
    && playwright install chrome \
    && rm -rf /tmp/google-chrome-stable_current_amd64.deb \
    && rm -rf /root/.cache \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/* \
    && useradd -m --shell /bin/bash llmuser


ARG CACHEBUST=1
USER llmuser
COPY llm /app/llm


ENV PYTHONPATH=/app

EXPOSE 5000

CMD ["python", "-u", "llm/main.py", "--listen"]
# CMD sleep 1h
