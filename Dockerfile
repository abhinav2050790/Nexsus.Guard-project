# Root Dockerfile — Railway services for Nexsus.Guard.
# Two build targets share the same dependency install:
#   default / api       -> uvicorn FastAPI
#   dashboard (target)  -> streamlit run dashboard/app.py
# Static-site detection was misfiring on root index.html; an explicit
# Dockerfile forces the correct runtime.

FROM python:3.12-slim AS base

WORKDIR /app

# Install dependencies first (cached layer)
COPY chargeback_evidence_responder/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the application
COPY chargeback_evidence_responder ./chargeback_evidence_responder

ENV MPLBACKEND=Agg \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# ── Target: api (default, final stage) ─────────────────────────────
FROM base AS api
WORKDIR /app/chargeback_evidence_responder
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

# ── Target: dashboard (build with --target dashboard) ─────────────
FROM base AS dashboard
WORKDIR /app/chargeback_evidence_responder
EXPOSE 8501
CMD ["sh", "-c", "exec streamlit run dashboard/app.py --server.port ${PORT:-8501} --server.address 0.0.0.0 --server.headless true --browser.gatherUsageStats false"]
