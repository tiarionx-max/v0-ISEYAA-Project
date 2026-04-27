FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev curl && rm -rf /var/lib/apt/lists/*

FROM base AS dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

FROM dependencies AS development
COPY requirements-dev.txt* ./
RUN pip install pytest pytest-asyncio pytest-cov httpx 2>/dev/null || true
COPY . .
RUN groupadd -r iseyaa && useradd -r -g iseyaa iseyaa && chown -R iseyaa:iseyaa /app
USER iseyaa
EXPOSE 8003
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003", "--reload"]

FROM dependencies AS production
COPY . .
RUN groupadd -r iseyaa && useradd -r -g iseyaa iseyaa && chown -R iseyaa:iseyaa /app
USER iseyaa
HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD curl -f http://localhost:8003/health || exit 1
EXPOSE 8003
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003", "--workers", "2"]
