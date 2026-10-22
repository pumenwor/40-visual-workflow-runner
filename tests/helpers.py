import time
import uuid

API = "/api/v1"


def node(id, name, kind, config=None, order=0, retries=0, delay=0, timeout=10):
    return {
        "id": id, "name": name, "kind": kind, "config": config or {},
        "position": {"x": order * 200, "y": 100}, "sort_order": order,
        "max_retries": retries, "retry_delay_seconds": delay,
        "timeout_seconds": timeout,
    }


def edge(src, dst):
    return {"source_node_id": src, "target_node_id": dst}


def create_workflow(client, name=None):
    r = client.post(f"{API}/workflows",
                    json={"name": name or f"wf-{uuid.uuid4().hex[:8]}",
                          "description": "test"})
    assert r.status_code == 201, r.text
    return r.json()


def save_graph(client, wf_id, nodes, edges, version=None):
    if version is None:
        version = client.get(f"{API}/workflows/{wf_id}").json()["version"]
    return client.put(f"{API}/workflows/{wf_id}/graph",
                      json={"expected_version": version,
                            "nodes": nodes, "edges": edges})


def start_run(client, wf_id):
    return client.post(f"{API}/workflows/{wf_id}/runs")


def wait_for_run(client, run_id, timeout=8):
    deadline = time.time() + timeout
    while time.time() < deadline:
        run = client.get(f"{API}/runs/{run_id}").json()
        if run["status"] in ("succeeded", "failed"):
            return run
        time.sleep(0.3)
    raise AssertionError(f"Run {run_id} did not finish in {timeout}s")


def tasks_by_name(run):
    # Adjust "tasks" / "node_name_snapshot" if your API names differ
    return {t["node_name_snapshot"]: t for t in run["tasks"]}