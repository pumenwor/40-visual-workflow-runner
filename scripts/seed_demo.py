"""Create the three demo workflows through the public API.

Run the application first, then run:

    python scripts/seed_demo.py

Set APP_BASE_URL if the app is not at http://127.0.0.1:8000.
Running the script again skips workflows whose names already exist.
"""

from __future__ import annotations

import os
import uuid

import httpx

BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
API = f"{BASE_URL}/api/v1"


SAMPLES = [
    {
        "name": "Success demo",
        "description": "Two source values combine successfully.",
        "nodes": [
            ("a", "Source A", "emit_json", {"value": {"value": 3}}, 50, 60, 0, 0),
            ("b", "Source B", "emit_json", {"value": {"value": 4}}, 50, 220, 1, 0),
            ("c", "Combine", "combine_inputs", {}, 360, 140, 2, 0),
        ],
        "edges": [("a", "c"), ("b", "c")],
    },
    {
        "name": "Retry demo",
        "description": "A demo task fails once, then succeeds on retry.",
        "nodes": [
            ("a", "Source", "emit_json", {"value": {"value": 10}}, 50, 140, 0, 0),
            (
                "f",
                "Flaky task",
                "demo_fail",
                {"fail_first_n_attempts": 1, "value": {"message": "Recovered"}},
                320,
                140,
                1,
                1,
            ),
            ("c", "Combine", "combine_inputs", {}, 600, 140, 2, 0),
        ],
        "edges": [("a", "f"), ("f", "c")],
    },
    {
        "name": "Failure demo",
        "description": "A demo task exhausts retries; downstream work is skipped.",
        "nodes": [
            ("a", "Source", "emit_json", {"value": {"value": 7}}, 50, 140, 0, 0),
            (
                "f",
                "Broken task",
                "demo_fail",
                {"fail_first_n_attempts": 99, "value": {"message": "Never reached"}},
                320,
                140,
                1,
                1,
            ),
            ("c", "Combine", "combine_inputs", {}, 600, 140, 2, 0),
        ],
        "edges": [("a", "f"), ("f", "c")],
    },
]


def _request(client: httpx.Client, method: str, path: str, **kwargs):
    response = client.request(method, f"{API}{path}", **kwargs)
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise SystemExit(f"{method} {path} failed: {response.text}") from exc
    return response.json()


def main() -> None:
    try:
        with httpx.Client(timeout=10.0) as client:
            health = client.get(f"{BASE_URL}/healthz")
            health.raise_for_status()
            existing = _request(client, "GET", "/workflows")
            existing_names = {workflow["name"] for workflow in existing}

            for sample in SAMPLES:
                if sample["name"] in existing_names:
                    print(f"Skip existing workflow: {sample['name']}")
                    continue

                workflow = _request(
                    client,
                    "POST",
                    "/workflows",
                    json={
                        "name": sample["name"],
                        "description": sample["description"],
                    },
                )

                suffix = uuid.uuid4().hex[:8]
                id_map: dict[str, str] = {}
                nodes = []
                for logical_id, name, kind, config, x, y, order, retries in sample["nodes"]:
                    node_id = f"{logical_id}-{suffix}"
                    id_map[logical_id] = node_id
                    nodes.append(
                        {
                            "id": node_id,
                            "name": name,
                            "kind": kind,
                            "config": config,
                            "position": {"x": x, "y": y},
                            "sort_order": order,
                            "max_retries": retries,
                            "retry_delay_seconds": 0,
                            "timeout_seconds": 10,
                        }
                    )

                edges = [
                    {
                        "source_node_id": id_map[source],
                        "target_node_id": id_map[target],
                    }
                    for source, target in sample["edges"]
                ]
                _request(
                    client,
                    "PUT",
                    f"/workflows/{workflow['id']}/graph",
                    json={
                        "expected_version": workflow["version"],
                        "nodes": nodes,
                        "edges": edges,
                    },
                )
                print(f"Created workflow: {sample['name']}")
    except httpx.ConnectError as exc:
        raise SystemExit(
            f"Could not connect to {BASE_URL}. Start the app first with: "
            "uvicorn app.main:app --reload"
        ) from exc


if __name__ == "__main__":
    main()
