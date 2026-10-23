from tests.helpers import *


def build_success(client):
    wf = create_workflow(client)
    save = save_graph(client, wf["id"],
        [node("a", "Source A", "emit_json", {"value": 1}, 0),
         node("b", "Source B", "emit_json", {"value": 2}, 1),
         node("c", "Combine", "combine_inputs", {}, 2)],
        [edge("a", "c"), edge("b", "c")])
    assert save.status_code == 200, save.text
    return wf


def test_health(client):
    r = client.get("/healthz")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_create_list_read(client):
    wf = create_workflow(client, "Listed workflow")
    assert any(w["id"] == wf["id"] for w in client.get(f"{API}/workflows").json())
    assert client.get(f"{API}/workflows/{wf['id']}").status_code == 200


def test_missing_workflow_404(client):
    assert client.get(f"{API}/workflows/does-not-exist").status_code == 404
    assert client.get(f"{API}/runs/does-not-exist").status_code == 404


def test_save_and_reload_graph(client):
    wf = build_success(client)
    data = client.get(f"{API}/workflows/{wf['id']}").json()
    assert len(data["nodes"]) == 3 and len(data["edges"]) == 2
    assert {n["position"]["x"] for n in data["nodes"]} == {0, 200, 400}


def test_version_conflict(client):
    wf = build_success(client)
    r = save_graph(client, wf["id"], [node("a", "A", "emit_json", {"value": 1})],
                   [], version=999)
    assert r.status_code == 409


def test_validate_valid_graph(client):
    wf = build_success(client)
    r = client.post(f"{API}/workflows/{wf['id']}/validate").json()
    assert r["valid"] is True
    assert r["execution_order"] == ["a", "b", "c"]


def test_cycle_rejected(client):
    wf = create_workflow(client)
    save_graph(client, wf["id"],
        [node("a", "A", "emit_json", {"value": 1}, 0),
         node("b", "B", "combine_inputs", {}, 1)],
        [edge("a", "b"), edge("b", "a")])
    r = client.post(f"{API}/workflows/{wf['id']}/validate").json()
    assert r["valid"] is False and r["errors"]
    assert client.post(f"{API}/workflows/{wf['id']}/runs").status_code in (409, 422)


def test_self_edge_and_missing_endpoint_rejected(client):
    wf = create_workflow(client)
    r = save_graph(client, wf["id"], [node("a", "A", "emit_json", {"value": 1})],
                   [edge("a", "a")])
    assert r.status_code == 422
    r = save_graph(client, wf["id"], [node("a", "A", "emit_json", {"value": 1})],
                   [edge("a", "ghost")])
    assert r.status_code == 422


def test_successful_run_passes_parent_outputs(client):
    wf = build_success(client)
    r = start_run(client, wf["id"])
    assert r.status_code == 202, r.text
    run = wait_for_run(client, r.json()["id"])
    assert run["status"] == "succeeded"
    t = tasks_by_name(run)
    assert t["Combine"]["status"] == "succeeded"
    assert t["Combine"]["output"] == {"inputs": {"a": 1, "b": 2}}


def test_retry_then_success(client):
    wf = create_workflow(client)
    save_graph(client, wf["id"],
        [node("f", "Flaky", "demo_fail",
              {"fail_first_n_attempts": 1, "value": "ok"}, 0, retries=1)], [])
    run = wait_for_run(client, start_run(client, wf["id"]).json()["id"])
    assert run["status"] == "succeeded"
    t = tasks_by_name(run)["Flaky"]
    assert t["attempt_count"] == 2
    assert [a["status"] for a in t["attempts"]] == ["failed", "succeeded"]


def test_retry_exhausted_skips_downstream(client):
    wf = create_workflow(client)
    save_graph(client, wf["id"],
        [node("f", "Broken", "demo_fail",
              {"fail_first_n_attempts": 5, "value": "x"}, 0, retries=1),
         node("d", "Downstream", "combine_inputs", {}, 1)],
        [edge("f", "d")])
    run = wait_for_run(client, start_run(client, wf["id"]).json()["id"])
    assert run["status"] == "failed"
    t = tasks_by_name(run)
    assert t["Broken"]["status"] == "failed"
    assert t["Broken"]["attempt_count"] == 2
    assert t["Downstream"]["status"] == "skipped"
    assert "Traceback" not in str(run)


def test_run_snapshot_unchanged_after_edit(client):
    wf = build_success(client)
    run = wait_for_run(client, start_run(client, wf["id"]).json()["id"])
    # edit the workflow: rename a node
    save_graph(client, wf["id"],
        [node("a", "RENAMED", "emit_json", {"value": 9}, 0)], [])
    old = client.get(f"{API}/runs/{run['id']}").json()
    assert "Source A" in tasks_by_name(old)
    assert "RENAMED" not in tasks_by_name(old)


def test_run_history_newest_first(client):
    wf = build_success(client)
    r1 = wait_for_run(client, start_run(client, wf["id"]).json()["id"])
    r2 = wait_for_run(client, start_run(client, wf["id"]).json()["id"])
    runs = client.get(f"{API}/workflows/{wf['id']}/runs?limit=20").json()
    ids = [r["id"] for r in runs]
    assert ids.index(r2["id"]) < ids.index(r1["id"])


def test_history_survives_new_client(client):
    """Simulates refresh/restart: a fresh client on the same DB sees old runs."""
    from fastapi.testclient import TestClient
    from app.main import app
    wf = build_success(client)
    run = wait_for_run(client, start_run(client, wf["id"]).json()["id"])
    with TestClient(app) as fresh:
        assert fresh.get(f"{API}/runs/{run['id']}").status_code == 200


def test_invalid_payload_is_4xx_not_500(client):
    wf = create_workflow(client)
    r = client.put(f"{API}/workflows/{wf['id']}/graph", json={"nodes": "nope"})
    assert 400 <= r.status_code < 500