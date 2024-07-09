FROM python:3.12-slim AS builder

WORKDIR /app

COPY requirements.txt ./

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential xvfb xauth python3-tk python3-dev \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir nuitka

ARG CACHEBUST=1
COPY llm /app/llm

ENV PYTHONPATH=/app
RUN nuitka3 --module --include-package=llm llm/main.py

FROM python:3.12-slim AS final

WORKDIR /app
COPY requirements.txt ./

RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-noto-cjk xvfb xauth python3-tk python3-dev \
    && pip install --no-cache-dir -r requirements.txt \
    && playwright install chrome \
    && rm -rf /tmp/google-chrome-stable_current_amd64.deb \
    && rm -rf /root/.cache \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/* \
    && useradd -m --shell /bin/bash llmuser

ARG CACHEBUST=1

COPY --from=builder /app/*.so /app/main.pyi ./
COPY run.py ./

USER llmuser
ENV PYTHONPATH=/app

EXPOSE 5000

CMD ["python", "-u", "run.py", "--listen"]