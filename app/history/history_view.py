import streamlit as st


def _task_name(task_id, workflow):
    """Find a task's display name from the workflow. Falls back to its id.

    Later we can swap this for Person 1's node_name() helper.
    """
    for node in workflow.get("nodes", []):
        if node.get("id") == task_id:
            return node.get("name", task_id)
    return task_id


def _is(status, word):
    """Compare statuses ignoring capital letters ("Success" == "success")."""
    return str(status).lower() == word


def render_history(workflow, runs=None):
    """Draw the run history for one workflow.

    workflow: the workflow Person 1 has selected (has "name" and "nodes")
    runs:     a list of run dictionaries from run_workflow() or the database.
              Each run has "status" and "tasks" (a dictionary keyed by task id).
    """
    st.subheader(f"History for: {workflow['name']}")

    if not runs:
        st.info("This workflow has not been run yet.")
        return

    # Part 1: the list of runs
    rows = []
    for number, run in enumerate(runs, start=1):
        rows.append({
            "Run": run.get("id", number),
            "Status": str(run["status"]).upper(),
            "Tasks": len(run["tasks"]),
        })
    st.table(rows)

    # Part 2: details of the run the user picks
    run_ids = [row["Run"] for row in rows]
    chosen_id = st.selectbox("Pick a run", run_ids)
    chosen_run = runs[run_ids.index(chosen_id)]

    if _is(chosen_run["status"], "success") or _is(chosen_run["status"], "succeeded"):
        st.success(f"Run {chosen_id} succeeded")
    else:
        st.error(f"Run {chosen_id} failed")

    # Part 3: every task, in the order it ran
    for task_id, task in chosen_run["tasks"].items():
        name = _task_name(task_id, workflow)
        tries = len(task["attempts"])
        title = f"{name}: {task['status']} ({tries} tries)"

        with st.expander(title, expanded=True):
            if _is(task["status"], "skipped"):
                st.info(task.get("error") or "Skipped because an earlier task failed.")
                continue

            finished_ok = _is(task["status"], "success") or _is(task["status"], "succeeded")

            st.write("Attempts:")
            for attempt in task["attempts"]:
                line = f"Attempt {attempt['attempt']}: {attempt['status']}"
                if attempt["error"]:
                    if finished_ok:
                        line += f" (recovered by retry) - {attempt['error']}"
                    else:
                        line += f" - {attempt['error']}"
                st.write(line)

            if task["output"] is not None:
                st.write("Output:")
                st.json(task["output"])

            if not finished_ok and task["error"]:
                st.error(f"Final error: {task['error']}")