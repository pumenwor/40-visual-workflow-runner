"""Routes for the browser UI.

The API remains under /api/v1. These routes only serve the single-page
browser shell; all workflow and run data is loaded through the public API.
That keeps the UI honest: it exercises the same contract as API clients.
"""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, Response

router = APIRouter(include_in_schema=False)
STATIC_DIR = Path(__file__).parent / "static"
INDEX_FILE = STATIC_DIR / "index.html"


def _index() -> FileResponse:
    return FileResponse(INDEX_FILE)


@router.get("/")
def dashboard() -> FileResponse:
    return _index()


@router.get("/workflows/{workflow_id}")
def workflow_page(workflow_id: str) -> FileResponse:
    return _index()


@router.get("/workflows/{workflow_id}/history")
def workflow_history_page(workflow_id: str) -> FileResponse:
    return _index()


@router.get("/runs/{run_id}")
def run_page(run_id: str) -> FileResponse:
    return _index()


@router.get("/favicon.ico")
def favicon() -> Response:
    # Avoid noisy 404s in otherwise healthy server logs.
    return Response(status_code=204)
