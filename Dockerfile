# syntax=docker/dockerfile:1
FROM python:3.13.7-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY pyproject.toml README.md LICENSE ./
COPY flannel ./flannel

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

CMD ["flannel"]
