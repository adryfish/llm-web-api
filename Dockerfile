FROM ubuntu:22.04

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip xvfb

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 1

RUN useradd -m --shell /bin/bash llmuser \
    && chown -R llmuser:llmuser .

COPY requirements.txt .
RUN pip install -r requirements.txt --index-url https://mirrors.cloud.tencent.com/pypi/simple --trusted-host mirrors.cloud.tencent.com \
    && rm -rf /root/.cache

RUN playwright install chrome

USER llmuser
COPY llm /app/llm

ENV PYTHONPATH=/app
ENV NO_GUI=true

EXPOSE 5000

CMD ["/usr/bin/python", "-u", "llm/main.py", "--listen"]
# CMD sleep 1h
