# Visual Workflow Runner

A small web app to build task nodes, connect them as a dependency graph,
validate the graph, run it in order, and inspect results, retries and failures.

> **Demo only.** No login, not for sensitive or production data.

## What it does (MVP)
- Create and save workflows made of nodes and connections
- Validate: missing nodes, duplicate or self connections, cycles
- Run nodes in a stable dependency order, one at a time
- Retry failed nodes (0-3 times) and record every attempt
- Show run history: status, outputs, attempts, errors

## What it does not do
No user code or shell commands, no outbound network calls from tasks,
no parallel runs, no scheduling, no login, no cancel or resume.

## Setup
Requires Python 3.12+.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # Windows: copy .env.example .env
alembic upgrade head
```

## Run
```bash
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000. Health check: http://127.0.0.1:8000/healthz

## Demo data
Start the app with `ENABLE_DEMO_NODE=true` in `.env`, then in a second terminal:
```bash
python scripts/seed_demo.py
```
It creates three sample workflows (success, retry-then-success, failure).
Running it again will not create duplicates.

## Tests and lint
```bash
pytest
ruff check .
```

## Environment variables
| Variable | Purpose | Default |
|---|---|---|
| DATABASE_URL | Database connection | sqlite:///./workflow_runner.db |
| APP_ENV | Environment label | development |
| ENABLE_DEMO_NODE | Enables the `demo_fail` test node | false |
| MAX_CONCURRENT_RUNS | Runs executing at once | 1 |
| LOG_LEVEL | Log detail | INFO |
| PORT | Port when the host sets one | 8000 |

## Node types
- `emit_json`: returns the JSON value in its config
- `combine_inputs`: returns the outputs of its direct parents
- `delay`: waits 0-5 seconds, then returns its inputs
- `demo_fail`: fails the first N attempts, then succeeds (demo only)

## Main API endpoints
| Method and path | Purpose |
|---|---|
| GET /healthz | Health check |
| POST /api/v1/workflows | Create a workflow |
| GET /api/v1/workflows | List workflows |
| GET /api/v1/workflows/{id} | Read a workflow, nodes and edges |
| PUT /api/v1/workflows/{id}/graph | Save the whole graph |
| POST /api/v1/workflows/{id}/validate | Validate the saved graph |
| POST /api/v1/workflows/{id}/runs | Start a run |
| GET /api/v1/workflows/{id}/runs | List recent runs |
| GET /api/v1/runs/{run_id} | Run detail with tasks and attempts |

## Architecture
- `app/graph/`: pure validation and ordering logic
- `app/engine/`: task handlers, runner, retries
- `app/api/`, `app/db/`, `app/services/`: HTTP, database, business logic
- `app/web/`: pages, templates, static files

## Known limitations
No authentication, single-instance in-process worker, sequential execution,
no arbitrary code or network tasks, no cancel or resume. A run interrupted by a
restart is marked failed.

## Troubleshooting
- **Port in use:** run `uvicorn app.main:app --port 8001`
- **No such table:** run `alembic upgrade head`
- **database is locked:** keep `MAX_CONCURRENT_RUNS=1` with SQLite
- **demo_fail rejected:** set `ENABLE_DEMO_NODE=true` and restart

## Demo
See `docs/demo_script.md`.