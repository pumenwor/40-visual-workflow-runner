import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes_runs import router as runs_router
from app.api.routes_workflows import router as workflows_router
from app.config import LOG_LEVEL
from app.db.repositories import SqlRunRepository
from app.errors import AppError
from app.web.routes import router as web_router

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("app")

@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Mark runs left in ``running`` by a previous process as interrupted."""
    try:
        recovered = SqlRunRepository().recover_interrupted_runs()
        if recovered:
            logger.warning("Marked %s interrupted run(s) as failed", len(recovered))
    except Exception:
        # A not-yet-migrated database should not prevent the process from
        # starting far enough to report the real error on API use.
        logger.exception("Could not recover interrupted runs at startup")
    yield


app = FastAPI(title="Visual Workflow Runner", lifespan=lifespan)
app.include_router(workflows_router)
app.include_router(runs_router)
app.include_router(web_router)
app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).parent / "web" / "static"),
    name="static",
)


def error_response(status_code: int, code: str, message: str, details: list | None = None):
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details or []}},
    )


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return error_response(exc.status_code, exc.code, exc.message, exc.details)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    details = [
        {"field": ".".join(str(part) for part in err["loc"]), "message": err["msg"]}
        for err in exc.errors()
    ]
    return error_response(
        422, "INVALID_REQUEST", "The request body or parameters are invalid.", details
    )


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException):
    codes = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}
    code = codes.get(exc.status_code, "HTTP_ERROR")
    return error_response(exc.status_code, code, str(exc.detail))


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception):
    # The full details go to the server log, never to the user.
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return error_response(500, "INTERNAL_ERROR", "An unexpected error occurred.")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}