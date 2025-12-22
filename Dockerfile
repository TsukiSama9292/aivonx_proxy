FROM python:3.12-slim-bookworm

RUN apt-get update && \
    apt-get install -y \
    curl

RUN curl -LsSf https://astral.sh/uv/0.9.8/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"
RUN apt-get clean && rm -rf /var/lib/apt/lists/*
ENV PYTHONDONTWRITEBYTECODE=1

RUN mkdir -p /app
COPY . /app/
WORKDIR /app
RUN uv sync
ENV PORT=8000