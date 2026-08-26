"""FastAPI application entry point.

Run with:
    uvicorn api.main:app --reload --port 8000   (from the package directory)
"""

from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent.parent
if str(PACKAGE_DIR) not in sys.path:
    sys.path.insert(0, str(PACKAGE_DIR))

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from api.routes import LETTER_CACHE, load_artifacts, router, state
from api.schemas import ErrorResponse, HealthResponse
from utils.db import db_manager
from utils.logger import get_logger

logger = get_logger()

app = FastAPI(
    title="Chargeback Evidence Responder API",
    description="AI defence-only chargeback analysis: win-probability scoring, "
                "evidence assessment and rebuttal letter generation.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info("{} {} -> {} ({:.0f} ms)",
                request.method, request.url.path, response.status_code, elapsed_ms)
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    chargeback_id = ""
    try:
        body_path = request.path_params.get("chargeback_id", "")
        chargeback_id = str(body_path)
    except Exception:
        pass
    logger.error("Unhandled error on {} {}: {}",
                 request.method, request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(error=str(exc), chargeback_id=chargeback_id).model_dump(),
    )


@app.on_event("startup")
def startup() -> None:
    logger.info("Starting Chargeback Evidence Responder API ...")
    load_artifacts()
    logger.info("Startup complete.")


app.include_router(router)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    db_connected = False
    try:
        from sqlalchemy import text
        with db_manager.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_connected = True
    except Exception as exc:
        logger.warning("Health DB check failed: {}", exc)

    return HealthResponse(
        status="ok",
        model_loaded=bool(state.ready),
        db_connected=db_connected,
        timestamp=datetime.now(),
    )


@app.get("/download-letter/{chargeback_id}")
def download_letter(chargeback_id: str) -> FileResponse:
    docx_path = PACKAGE_DIR / "data" / f"_letter_{chargeback_id}.docx"
    if chargeback_id in LETTER_CACHE:
        docx_path.write_bytes(LETTER_CACHE[chargeback_id])
    else:
        cached = PACKAGE_DIR / "model" / "artifacts" / "sample_letter_CB001.docx"
        if not cached.exists():
            return JSONResponse(status_code=404, content={
                "error": f"No letter generated for chargeback '{chargeback_id}'",
                "chargeback_id": chargeback_id,
            })
        docx_path = cached
    return FileResponse(
        path=docx_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"rebuttal_{chargeback_id}.docx",
    )
