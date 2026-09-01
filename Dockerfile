# Root Dockerfile — Railway services for Nexsus.Guard.
# Static-site detection was misfiring on root index.html; an explicit
# Dockerfile forces the correct Python runtime.
#
# One image serves both Railway services via SERVICE_ROLE:
#   SERVICE_ROLE=api       (default) -> uvicorn FastAPI on $PORT
#   SERVICE_ROLE=dashboard            -> streamlit run dashboard/app.py on $PORT

FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY chargeback_evidence_responder/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the application
COPY chargeback_evidence_responder ./chargeback_evidence_responder

WORKDIR /app/chargeback_evidence_responder

ENV MPLBACKEND=Agg \
    PYTHONUNBUFFERED=1 \
    SERVICE_ROLE=api

EXPOSE 8000

COPY docker-start.sh /usr/local/bin/docker-start.sh
RUN chmod +x /usr/local/bin/docker-start.sh

CMD ["/usr/local/bin/docker-start.sh"]
