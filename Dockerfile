FROM python:3.12-slim AS builder

WORKDIR /app
COPY requirements.txt setup.py /app/

RUN apt-get update \
    && apt-get install -y --no-install-recommends xvfb xauth python3-tk python3-dev build-essential \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir cython

ARG CACHEBUST=1
COPY llm /app/llm

ENV PYTHONPATH=/app
RUN python setup.py build_ext


FROM python:3.12-slim AS final

WORKDIR /app
COPY requirements.txt run.py /app/

RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-noto-cjk xvfb xauth python3-tk python3-dev \
    && pip install --no-cache-dir -r requirements.txt \
    && playwright install chrome \
    && rm -rf /tmp/google-chrome-stable_current_amd64.deb \
    && rm -rf /root/.cache \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/* \
    && useradd -m --shell /bin/bash llmuser

USER llmuser

ARG CACHEBUST=1
COPY --from=builder /app/build/dist/ /app/

ENV PYTHONPATH=/app

EXPOSE 5000

CMD ["python", "-u", "run.py", "--listen"]