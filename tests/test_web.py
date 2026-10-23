def test_root_serves_browser_ui(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Visual Workflow Runner" in response.text
    assert 'id="workflow-list"' in response.text


def test_workflow_and_run_pages_serve_browser_shell(client):
    for path in ("/workflows/example-id", "/workflows/example-id/history", "/runs/example-id"):
        response = client.get(path)
        assert response.status_code == 200, path
        assert response.headers["content-type"].startswith("text/html")
        assert "Visual Workflow Runner" in response.text


def test_browser_static_assets_are_mounted(client):
    script = client.get("/static/app.js")
    assert script.status_code == 200
    assert "loadWorkflows" in script.text

    styles = client.get("/static/styles.css")
    assert styles.status_code == 200
    assert ".node-card" in styles.text
