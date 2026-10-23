from app.history.sample_runs import runs

ALLOWED_RUN_STATUSES = {"Success", "Failed"}
ALLOWED_TASK_STATUSES = {"Success", "Failed", "Skipped"}


def test_every_run_has_a_valid_status():
    for run in runs:
        assert run["status"] in ALLOWED_RUN_STATUSES


def test_every_task_has_the_expected_fields():
    expected = {"status", "output", "error", "attempts"}
    for run in runs:
        for task in run["tasks"].values():
            assert set(task.keys()) == expected


def test_every_task_has_a_valid_status():
    for run in runs:
        for task in run["tasks"].values():
            assert task["status"] in ALLOWED_TASK_STATUSES


def test_skipped_tasks_have_no_attempts():
    for run in runs:
        for task in run["tasks"].values():
            if task["status"] == "Skipped":
                assert task["attempts"] == []


def test_attempts_are_numbered_from_one():
    for run in runs:
        for task in run["tasks"].values():
            numbers = [attempt["attempt"] for attempt in task["attempts"]]
            assert numbers == list(range(1, len(numbers) + 1))


def test_last_attempt_matches_final_task_status():
    for run in runs:
        for task in run["tasks"].values():
            if task["status"] in ("Success", "Failed"):
                assert task["attempts"][-1]["status"] == task["status"]


def test_failed_run_contains_a_failed_task():
    for run in runs:
        if run["status"] == "Failed":
            statuses = [task["status"] for task in run["tasks"].values()]
            assert "Failed" in statuses


def test_successful_run_has_only_successful_tasks():
    for run in runs:
        if run["status"] == "Success":
            for task in run["tasks"].values():
                assert task["status"] == "Success"


def test_outputs_contain_exactly_the_successful_tasks():
    for run in runs:
        succeeded = {
            node_id for node_id, task in run["tasks"].items()
            if task["status"] == "Success"
        }
        assert set(run["outputs"].keys()) == succeeded