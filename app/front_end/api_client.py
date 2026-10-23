import requests

API_BASE_URL = "http://127.0.0.1:8000/api/v1"


def _check(response):
    response.raise_for_status()
    return response.json()


def api_error_message(error):
    """Return the backend's readable error message when there is one."""
    try:
        return error.response.json()["error"]["message"]
    except Exception:
        return str(error)


def list_workflows():
    return _check(requests.get(f"{API_BASE_URL}/workflows", timeout=10))


def create_workflow(name, description=None):
    return _check(requests.post(
        f"{API_BASE_URL}/workflows",
        json={"name": name, "description": description},
        timeout=10,
    ))


def get_workflow(workflow_id):
    return _check(requests.get(f"{API_BASE_URL}/workflows/{workflow_id}", timeout=10))


def save_workflow_graph(workflow_id, expected_version, nodes, edges):
    return _check(requests.put(
        f"{API_BASE_URL}/workflows/{workflow_id}/graph",
        json={"expected_version": expected_version, "nodes": nodes, "edges": edges},
        timeout=10,
    ))


def validate_workflow(workflow_id):
    return _check(requests.post(f"{API_BASE_URL}/workflows/{workflow_id}/validate", timeout=10))


def create_run(workflow_id):
    return _check(requests.post(f"{API_BASE_URL}/workflows/{workflow_id}/runs", timeout=10))


def get_run(run_id):
    return _check(requests.get(f"{API_BASE_URL}/runs/{run_id}", timeout=10))


def list_runs(workflow_id, limit=20):
    return _check(requests.get(
        f"{API_BASE_URL}/workflows/{workflow_id}/runs",
        params={"limit": limit},
        timeout=10,
    ))


def convert_workflow_for_ui(workflow):
    """Convert backend data to the frontend format."""
    tasks = [
        {
            "id": n["id"],
            "name": n["name"],
            "type": n["kind"],
            "settings": n.get("config", {}),
        }
        for n in workflow.get("nodes", [])
    ]
    connections = [
        {"source_id": e["source_node_id"], "target_id": e["target_node_id"]}
        for e in workflow.get("edges", [])
    ]
    return {
        "id": workflow["id"],
        "name": workflow["name"],
        "version": workflow["version"],
        "tasks": tasks,
        "connections": connections,
        "backend_nodes": workflow.get("nodes", []),
        "backend_edges": workflow.get("edges", []),
    }