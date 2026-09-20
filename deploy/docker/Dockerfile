FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY core ./core
COPY apps ./apps
COPY scripts ./scripts
COPY artifacts ./artifacts
COPY samples ./samples
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -e '.[ml]'
ENV PYTHONPATH=/app:/app/core
CMD ["uvicorn", "apps.api.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

