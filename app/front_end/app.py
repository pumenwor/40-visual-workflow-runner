import json
import time
import uuid

import requests
import streamlit as st

from api_client import (
    api_error_message,
    convert_workflow_for_ui,
    create_run as api_create_run,
    create_workflow as api_create_workflow,
    get_run as api_get_run,
    get_workflow as api_get_workflow,
    list_runs as api_list_runs,
    list_workflows as api_list_workflows,
    save_workflow_graph as api_save_workflow_graph,
    validate_workflow as api_validate_workflow,
)
from workflow_helpers import build_dot, node_name, would_create_cycle

DEFAULT_CONFIG = {
    "emit_json": '{"value": 1}',
    "combine_inputs": "{}",
    "delay": '{"seconds": 1}',
    "demo_fail": '{"fail_first_n_attempts": 1, "value": "ok"}',
}
TERMINAL = ("succeeded", "failed")


def render_run(run):
    """Show a run. Status is always text, not only colour."""
    st.write(f"**Run status:** {run['status']}")
    if run.get("error_summary"):
        st.error(run["error_summary"])
    for task in run["tasks"]:
        with st.container(border=True):
            st.markdown(
                f"**{task['node_name']}** ({task['node_kind']}): "
                f"{task['status']}, {task['attempt_count']} attempt(s)"
            )
            for a in task.get("attempts", []):
                line = f"Attempt {a['attempt_number']}: {a['status']}"
                if a.get("error_message"):
                    line += f" ({a['error_message']})"
                st.write(line)
            if task.get("output") is not None:
                st.json(task["output"])
            if task.get("error_message"):
                st.error(task["error_message"])


def save_graph(workflow_id, mutate):
    """Load the latest graph, apply mutate(nodes, edges), and save it."""
    wf = api_get_workflow(workflow_id)
    nodes = list(wf.get("nodes", []))
    edges = list(wf.get("edges", []))
    mutate(nodes, edges)
    api_save_workflow_graph(workflow_id, wf["version"], nodes, edges)


st.set_page_config(page_title="Visual Workflow Runner", page_icon="🔗", layout="wide")
st.title("Visual Workflow Runner")
st.write("Create workflows, add tasks, connect them, check, run, and review history.")
st.caption("Demo only: no login, do not enter secrets or sensitive data.")

if "selected_workflow_id" not in st.session_state:
    st.session_state.selected_workflow_id = None
if "last_check" not in st.session_state:
    st.session_state.last_check = None

tab_workflows, tab_graph, tab_run, tab_history = st.tabs(
    ["Workflows", "Graph Editor", "Check / Run", "History"]
)

selected_workflow = None

# ------------------------------------------------------------------ Workflows
with tab_workflows:
    st.header("Manage Workflows")

    with st.form("create_workflow_form"):
        workflow_name = st.text_input("Workflow name", placeholder="e.g. Customer Data Workflow")
        create_button = st.form_submit_button("Create Workflow")

    if create_button:
        if not workflow_name.strip():
            st.error("Please enter a name for the workflow.")
        else:
            try:
                new_wf = api_create_workflow(workflow_name.strip())
                st.session_state.selected_workflow_id = new_wf["id"]
                st.session_state.last_check = None
                st.rerun()
            except requests.HTTPError as error:
                st.error(f"Could not create workflow: {api_error_message(error)}")
            except Exception as error:
                st.error(f"Could not create workflow. Is the backend running on port 8000? ({error})")

    st.divider()

    try:
        workflows = api_list_workflows()
    except Exception as error:
        st.error(f"Could not load workflows. Is the backend running on port 8000? ({error})")
        workflows = []

    if not workflows:
        st.info("No workflows yet. Create your first workflow above.")
    else:
        names = {w["id"]: w["name"] for w in workflows}
        ids = list(names)
        previous = st.session_state.selected_workflow_id
        if previous not in ids:
            previous = ids[0]

        chosen = st.selectbox(
            "Select a workflow",
            options=ids,
            index=ids.index(previous),
            format_func=lambda i: names[i],
            key="workflow_selector",
        )
        st.session_state.selected_workflow_id = chosen

        try:
            backend_wf = api_get_workflow(chosen)
            selected_workflow = convert_workflow_for_ui(backend_wf)
            st.success(f"Selected: {selected_workflow['name']}")
            st.write(f"**Workflow ID:** {selected_workflow['id']}")
            st.write(f"**Version:** {selected_workflow['version']}")
            st.write(f"**Tasks:** {len(selected_workflow['tasks'])}")
            st.write(f"**Connections:** {len(selected_workflow['connections'])}")
        except Exception as error:
            st.error(f"Could not load workflow details: {error}")

# --------------------------------------------------------------- Graph editor
with tab_graph:
    st.header("Graph Editor")

    if selected_workflow is None:
        st.info("Create or select a workflow in the Workflows tab to begin.")
    else:
        workflow_id = selected_workflow["id"]
        st.subheader(selected_workflow["name"])

        st.markdown("### Add a Task")
        task_type = st.selectbox("Task type", list(DEFAULT_CONFIG), key="task_type_select")
        st.caption(
            "emit_json: needs value. combine_inputs: no settings. "
            "delay: seconds (0 to 5). demo_fail: fail_first_n_attempts and value."
        )

        with st.form("add_task_form"):
            task_name = st.text_input("Task name", placeholder="e.g. Source A")
            task_settings = st.text_area(
                "Task settings (JSON)",
                value=DEFAULT_CONFIG[task_type],
                key=f"settings_{task_type}",
            )
            retries = st.number_input("Retries (0 to 3)", min_value=0, max_value=3, value=0)
            add_task_button = st.form_submit_button("Add Task")

        if add_task_button:
            if not task_name.strip():
                st.error("Please enter a task name.")
            else:
                try:
                    config = json.loads(task_settings or "{}")
                except json.JSONDecodeError:
                    config = None
                    st.error("Task settings must be valid JSON.")

                if config is not None:
                    def add_node(nodes, edges):
                        nodes.append({
                            "id": str(uuid.uuid4()),
                            "name": task_name.strip(),
                            "kind": task_type,
                            "config": config,
                            "position": {"x": 0.0, "y": float(len(nodes) * 120)},
                            "sort_order": len(nodes),
                            "max_retries": int(retries),
                            "retry_delay_seconds": 1,
                            "timeout_seconds": 10,
                        })

                    try:
                        save_graph(workflow_id, add_node)
                        st.session_state.last_check = None
                        st.rerun()
                    except requests.HTTPError as error:
                        st.error(f"Could not save task: {api_error_message(error)}")
                    except Exception as error:
                        st.error(f"Could not save task: {error}")

        st.divider()

        try:
            selected_workflow = convert_workflow_for_ui(api_get_workflow(workflow_id))
        except Exception as error:
            st.error(f"Could not reload workflow: {error}")
            st.stop()

        tasks = selected_workflow["tasks"]
        connections = selected_workflow["connections"]

        st.markdown("### Tasks")
        if not tasks:
            st.info("No tasks yet. Add your first task above.")
        for task in tasks:
            with st.container(border=True):
                st.markdown(f"**{task['name']}**")
                st.write(f"Type: {task['type']}")
                st.code(json.dumps(task["settings"], indent=2), language="json")

        st.divider()
        st.markdown("### Connect Tasks")
        st.caption("An arrow means the source must finish before the target starts.")

        if len(tasks) < 2:
            st.info("Add at least two tasks before creating a connection.")
        else:
            labels = {t["id"]: t["name"] for t in tasks}
            with st.form("add_connection_form"):
                source_id = st.selectbox("Source task (runs first)", list(labels),
                                         format_func=lambda i: labels[i])
                target_id = st.selectbox("Target task (runs after)", list(labels),
                                         format_func=lambda i: labels[i])
                add_connection = st.form_submit_button("Add Connection")

            if add_connection:
                if source_id == target_id:
                    st.error("A task cannot connect to itself.")
                elif any(c["source_id"] == source_id and c["target_id"] == target_id
                         for c in connections):
                    st.error("This connection already exists.")
                elif would_create_cycle(selected_workflow, source_id, target_id):
                    st.error("This connection would create a circular path.")
                else:
                    def add_edge(nodes, edges):
                        edges.append({"source_node_id": source_id, "target_node_id": target_id})

                    try:
                        save_graph(workflow_id, add_edge)
                        st.session_state.last_check = None
                        st.rerun()
                    except requests.HTTPError as error:
                        st.error(f"Could not save connection: {api_error_message(error)}")
                    except Exception as error:
                        st.error(f"Could not save connection: {error}")

        st.divider()
        st.markdown("### Connections")
        if not connections:
            st.info("No connections yet.")
        for c in connections:
            st.write(f"{node_name(selected_workflow, c['source_id'])} ➡️ "
                     f"{node_name(selected_workflow, c['target_id'])}")

        st.divider()
        st.markdown("### Workflow Graph")
        if tasks:
            st.graphviz_chart(build_dot(selected_workflow))
        else:
            st.info("Add tasks to display the graph.")

# ------------------------------------------------------------------ Check/Run
with tab_run:
    st.header("Check and Run Workflow")

    if selected_workflow is None:
        st.info("Select a workflow in the Workflows tab first.")
    else:
        workflow_id = selected_workflow["id"]
        st.write(f"Selected workflow: **{selected_workflow['name']}**")

        st.subheader("Check Workflow")
        st.write("The backend validates the saved graph.")

        if st.button("Check Workflow", key="check_btn"):
            try:
                st.session_state.last_check = {
                    "workflow_id": workflow_id,
                    "result": api_validate_workflow(workflow_id),
                }
            except Exception as error:
                st.error(f"Could not check workflow: {error}")

        last = st.session_state.last_check
        if last and last["workflow_id"] == workflow_id:
            result = last["result"]
            if result["valid"]:
                st.success("The graph is valid.")
                st.write("Execution order: " + " → ".join(
                    node_name(selected_workflow, n) for n in result["execution_order"]))
            else:
                st.error("The graph has problems:")
                for issue in result["errors"]:
                    st.write(f"- [{issue['code']}] {issue['message']}")

        st.divider()
        st.subheader("Run Workflow")
        st.write("Runs the last saved version of the graph.")

        if st.button("Run Workflow", key="run_btn"):
            try:
                created = api_create_run(workflow_id)
            except requests.HTTPError as error:
                st.error(api_error_message(error))
                created = None
            except Exception as error:
                st.error(f"Could not start the run: {error}")
                created = None

            if created:
                placeholder = st.empty()
                for _ in range(40):
                    run = api_get_run(created["id"])
                    with placeholder.container():
                        render_run(run)
                    if run["status"] in TERMINAL:
                        break
                    time.sleep(1)
                else:
                    st.warning("Still running. Check the History tab for the result.")

# -------------------------------------------------------------------- History
with tab_history:
    st.header("Workflow Execution History")

    if selected_workflow is None:
        st.info("Select a workflow to view its history.")
    else:
        workflow_id = selected_workflow["id"]
        st.write(f"History for: **{selected_workflow['name']}**")
        st.button("Refresh history", key="refresh_history")

        try:
            runs = api_list_runs(workflow_id)
        except Exception as error:
            st.error(f"Could not load history: {error}")
            runs = []

        if not runs:
            st.info("No runs yet. Run the workflow in the Check / Run tab.")
        else:
            labels = {r["id"]: f"{r['created_at']}  ({r['status']})" for r in runs}
            run_id = st.selectbox("Select a run", list(labels), format_func=lambda i: labels[i])
            try:
                render_run(api_get_run(run_id))
            except Exception as error:
                st.error(f"Could not load the run: {error}")