import requests

API_BASE_URL = "http://127.0.0.1:8000/api/v1"


def list_workflows():
    """Retrieve all workflows from the backend."""
    response = requests.get(
        f"{API_BASE_URL}/workflows",
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def create_workflow(name, description=None):
    """Create a workflow through the backend."""
    response = requests.post(
        f"{API_BASE_URL}/workflows",
        json={
            "name": name,
            "description": description,
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def get_workflow(workflow_id):
    """Retrieve one workflow, including its nodes and edges."""
    response = requests.get(
        f"{API_BASE_URL}/workflows/{workflow_id}",
        timeout=10,
    )
    response.raise_for_status()
    return response.json()