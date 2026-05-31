# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy shared library first (enables layer caching)
COPY shared/telco-common /build/shared/telco-common

# Install the shared library into a prefix we can copy
RUN pip install --prefix=/install --no-cache-dir /build/shared/telco-common

# Copy service source
COPY services/inventory-service /build/service

# Install service dependencies (telco-common installed from local path)
RUN pip install --prefix=/install --no-cache-dir \
    --find-links /install/lib/python3.12/site-packages \
    /build/service


# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

LABEL maintainer="platform-engineering@telco.com"
LABEL service="inventory-service"
LABEL spec="TMF637"

# Non-root user
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --no-create-home --shell /bin/false appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy service source
COPY --from=builder /build/service /app

# Copy shared library source for the file:// reference
COPY --from=builder /build/shared/telco-common /app/shared/telco-common

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Expose service port
EXPOSE 8000

USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
