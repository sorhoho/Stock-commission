FROM python:3.12-slim AS base

WORKDIR /app

# Install system dependencies for hiredis
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy shared library first for layer caching
COPY shared/telco-common /app/shared/telco-common

# Copy service source
COPY services/stock-query-service/pyproject.toml /app/services/stock-query-service/pyproject.toml

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir /app/services/stock-query-service/[standard] 2>/dev/null || true \
    && pip install --no-cache-dir "fastapi>=0.111" "uvicorn[standard]>=0.30" \
       "pydantic>=2.7" "pydantic-settings>=2.3" "aiokafka>=0.10" \
       "redis[hiredis]>=5.0" "structlog>=24.2" \
       "prometheus-fastapi-instrumentator>=7.0" \
       "opentelemetry-api>=1.24" "opentelemetry-sdk>=1.24" \
       "opentelemetry-instrumentation-fastapi>=0.45b0" \
       "tenacity>=8.3" \
    && pip install --no-cache-dir /app/shared/telco-common

# Copy application source
COPY services/stock-query-service/app /app/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
