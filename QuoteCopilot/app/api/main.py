"""FastAPI application factory.

Registers the four routers and wires shared dependencies via deps.py. Defines
consistent error shapes: ``{error, field_errors}`` for validation failures and
``{error, run_id}`` for run-level failures.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.deps import init_context, shutdown_context
from app.api.routes import answers, quotes, reviews, runs


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_context()
    try:
        yield
    finally:
        shutdown_context()


def create_app() -> FastAPI:
    """Construct and configure the QuoteCopilot API."""
    app = FastAPI(
        title="QuoteCopilot API",
        version="1.0.0",
        description="Multi-agent HO3 underwriting review system.",
        lifespan=lifespan,
    )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(request: Request, exc: RequestValidationError):
        field_errors = [
            {"field": ".".join(str(p) for p in err.get("loc", [])), "msg": err.get("msg")}
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={"error": "Validation failed", "field_errors": field_errors},
        )

    @app.get("/health", tags=["system"])
    async def health() -> dict:
        return {"status": "ok"}

    app.include_router(quotes.router)
    app.include_router(runs.router)
    app.include_router(answers.router)
    app.include_router(reviews.router)
    return app


app = create_app()
