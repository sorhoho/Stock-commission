FROM python:3.11-slim AS builder

WORKDIR /build

ENV PIP_TRUSTED_HOST="pypi.org files.pythonhosted.org pypi.python.org" \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /app/shared
COPY shared/telco-common /app/shared/telco-common
RUN pip install --prefix=/install /app/shared/telco-common

COPY services/warehouse-service /build/service
RUN pip install --prefix=/install \
    --find-links /install/lib/python3.11/site-packages \
    /build/service


FROM python:3.11-slim AS runtime

RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --no-create-home --shell /bin/false appuser

WORKDIR /app

COPY --from=builder /install /usr/local
COPY --from=builder /build/service /app
COPY --from=builder /app/shared/telco-common /app/shared/telco-common

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

EXPOSE 8000

USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
