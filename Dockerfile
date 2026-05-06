FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends bash git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

RUN python3 tools/reference/synrail_install_v0.py --venv /opt/synrail-venv --project-root /app

ENV PATH="/opt/synrail-venv/bin:${PATH}"

CMD ["synrail", "--help"]
