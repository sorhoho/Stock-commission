# ─── Stage 1: build dependencies ────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        git \
    && rm -rf /var/lib/apt/lists/*

# Copy shared library first (referenced as a local path dep)
COPY shared/telco-common /build/shared/telco-common

# Copy service source
COPY services/sell-out-service /build/services/sell-out-service

# Install into a prefix we can copy
RUN pip install --upgrade pip \
 && pip install --prefix=/install \
        /build/shared/telco-common \
        /build/services/sell-out-service


# ─── Stage 2: runtime image ──────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Non-root user
RUN addgroup --system --gid 1000 appgroup \
 && adduser  --system --uid 1000 --ingroup appgroup appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy shared library source (editable-install path used at runtime)
COPY --chown=appuser:appgroup shared/telco-common /app/shared/telco-common

# Copy application source
COPY --chown=appuser:appgroup services/sell-out-service /app/services/sell-out-service

WORKDIR /app/services/sell-out-service

USER 1000

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
