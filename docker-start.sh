#!/bin/sh
# Role-based entrypoint: same image serves the API and the Streamlit dashboard.
set -e

PORT="${PORT:-8000}"

case "${SERVICE_ROLE:-api}" in
  dashboard)
    exec streamlit run dashboard/app.py \
      --server.port "${PORT}" \
      --server.address 0.0.0.0 \
      --server.headless true \
      --browser.gatherUsageStats false
    ;;
  api|*)
    exec uvicorn api.main:app --host 0.0.0.0 --port "${PORT}"
    ;;
esac
