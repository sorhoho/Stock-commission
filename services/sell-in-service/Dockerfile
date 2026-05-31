FROM python:3.12-slim AS builder
WORKDIR /build
RUN pip install hatchling
COPY shared/telco-common /build/shared/telco-common
COPY services/sell-in-service/pyproject.toml .
RUN pip install --no-cache-dir --target=/install .

FROM python:3.12-slim
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser
WORKDIR /app
COPY --from=builder /install /usr/local/lib/python3.12/site-packages/
COPY shared/telco-common /app/shared/telco-common
RUN cd /app/shared/telco-common && pip install --no-cache-dir -e .
COPY services/sell-in-service /app
RUN chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
