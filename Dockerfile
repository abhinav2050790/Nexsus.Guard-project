# Root Dockerfile — forces Railway to build the FastAPI service
# (Docker detection takes priority over static-site detection,
#  which was misfiring on the root index.html)
FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY chargeback_evidence_responder/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the application
COPY chargeback_evidence_responder ./chargeback_evidence_responder
COPY nixpacks.toml ./

WORKDIR /app/chargeback_evidence_responder

ENV MPLBACKEND=Agg \
    PYTHONUNBUFFERED=1 \
    PORT=8000

EXPOSE 8000

CMD ["sh", "-c", "exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
