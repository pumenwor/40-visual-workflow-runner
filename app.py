import sqlite3

import streamlit as st

from database import (
    init_db,
    create_workflow,
    list_workflows,
    add_task,
    add_connection,
    load_workflow,
    get_history,
)

from workflow_helpers import (
    node_name,
    build_dot,
    would_create_cycle,
    check_workflow,
)


# --------------------------------------------------
# 1. PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Visual Workflow Runner",
    page_icon="🔗",
    layout="wide",
)

st.title("Visual Workflow Runner")

st.write(
    "Create workflows, add tasks, connect them, "
    "and save your work."
)


# --------------------------------------------------
# 2. INITIALIZE THE DATABASE
# --------------------------------------------------

# Creates the database and tables if they do not exist.
init_db()


# Remember the selected workflow while the app is open.
if "selected_workflow_id" not in st.session_state:
    st.session_state.selected_workflow_id = None

# Remember the latest result of the Check button.
if "last_check" not in st.session_state:
    st.session_state.last_check = None


# --------------------------------------------------
# 3. CREATE THE APPLICATION TABS
# --------------------------------------------------

tab_workflows, tab_graph, tab_check_run, tab_history = st.tabs(
    [
        "Workflows",
        "Graph Editor",
        "Check / Run",
        "History",
    ]
)


# --------------------------------------------------
# 4. WORKFLOWS TAB
# --------------------------------------------------

selected_workflow = None

with tab_workflows:

    st.header("Manage Workflows")

    # ----------------------------------------------
    # Create a workflow
    # ----------------------------------------------

    with st.form("create_workflow_form"):

        workflow_name = st.text_input(
            "Workflow name",
            placeholder="e.g. Customer Data Workflow",
        )

        create_button = st.form_submit_button(
            "Create Workflow"
        )

    if create_button:

        if not workflow_name.strip():

            st.error(
                "Please enter a name for the workflow."
            )

        else:

            new_workflow_id = create_workflow(
                workflow_name.strip()
            )

            # Select the newly created workflow.
            st.session_state.selected_workflow_id = (
                new_workflow_id
            )

            # Clear any old Check results.
            st.session_state.last_check = None

            st.success(
                f"Workflow '{workflow_name.strip()}' created."
            )

            # Reload the app so the new workflow appears.
            st.rerun()

    st.divider()

    # ----------------------------------------------
    # Load the list of workflows
    # ----------------------------------------------

    workflows = list_workflows()

    if not workflows:

        st.info(
            "No workflows have been created yet. "
            "Create your first workflow above."
        )

    else:

        # Build a lookup of workflow IDs and names.
        workflow_names = {
            workflow["id"]: workflow["name"]
            for workflow in workflows
        }

        workflow_ids = list(workflow_names.keys())

        # Keep the previous selection if it still exists.
        previous_id = (
            st.session_state.selected_workflow_id
        )

        if previous_id not in workflow_ids:
            previous_id = workflow_ids[0]

        selected_index = workflow_ids.index(previous_id)

        selected_workflow_id = st.selectbox(
            "Select a workflow",
            options=workflow_ids,
            index=selected_index,
            format_func=lambda workflow_id: (
                workflow_names[workflow_id]
            ),
            key="workflow_selector",
        )

        # Store the current selection.
        st.session_state.selected_workflow_id = (
            selected_workflow_id
        )

        # Load the selected workflow from SQLite.
        selected_workflow = load_workflow(
            selected_workflow_id
        )

        if selected_workflow:

            st.success(
                f"Selected: {selected_workflow['name']}"
            )

            st.write(
                f"**Workflow ID:** "
                f"{selected_workflow['id']}"
            )

            st.write(
                f"**Created:** "
                f"{selected_workflow['created_at']}"
            )

            st.write(
                f"**Tasks:** "
                f"{len(selected_workflow['tasks'])}"
            )

            st.write(
                f"**Connections:** "
                f"{len(selected_workflow['connections'])}"
            )


# --------------------------------------------------
# 5. GRAPH EDITOR TAB
# --------------------------------------------------

with tab_graph:

    st.header("Graph Editor")

    if selected_workflow is None:

        st.info(
            "Create or select a workflow in the "
            "Workflows tab to begin."
        )

    else:

        workflow_id = selected_workflow["id"]

        st.subheader(selected_workflow["name"])

        # ------------------------------------------
        # Add a task
        # ------------------------------------------

        st.markdown("### Add a Task")

        with st.form("add_task_form"):

            task_name = st.text_input(
                "Task name",
                placeholder="e.g. Read Customer Data",
            )

            task_type = st.selectbox(
                "Task type",
                [
                    "Source",
                    "Transform",
                    "Output",
                    "Other",
                ],
            )

            task_settings = st.text_area(
                "Task settings",
                placeholder=(
                    "e.g. file_path: customers.csv"
                ),
            )

            add_task_button = st.form_submit_button(
                "Add Task"
            )

        if add_task_button:

            if not task_name.strip():

                st.error(
                    "Please enter a task name."
                )

            else:

                add_task(
                    workflow_id=workflow_id,
                    name=task_name,
                    task_type=task_type,
                    settings=task_settings,
                )

                st.session_state.last_check = None

                st.success(
                    f"Task '{task_name.strip()}' saved."
                )

                # Reload from SQLite.
                st.rerun()

        st.divider()

        # ------------------------------------------
        # Reload the workflow after database changes
        # ------------------------------------------

        selected_workflow = load_workflow(
            workflow_id
        )

        tasks = selected_workflow["tasks"]
        connections = selected_workflow["connections"]

        # ------------------------------------------
        # Display tasks
        # ------------------------------------------

        st.markdown("### Tasks")

        if not tasks:

            st.info(
                "No tasks yet. Add your first task above."
            )

        else:

            for task in tasks:

                with st.container(border=True):

                    st.markdown(
                        f"**{task['name']}**"
                    )

                    st.write(
                        f"ID: {task['id']}"
                    )

                    st.write(
                        f"Type: {task['type']}"
                    )

                    if task["settings"]:

                        st.write(
                            f"Settings: {task['settings']}"
                        )

        st.divider()

        # ------------------------------------------
        # Connect two tasks
        # ------------------------------------------

        st.markdown("### Connect Tasks")

        if len(tasks) < 2:

            st.info(
                "Add at least two tasks before "
                "creating a connection."
            )

        else:

            # Map task IDs to readable labels.
            task_labels = {
                task["id"]: (
                    f"{task['name']} "
                    f"(ID: {task['id']})"
                )
                for task in tasks
            }

            task_ids = list(task_labels.keys())

            with st.form("add_connection_form"):

                source_id = st.selectbox(
                    "Source task",
                    options=task_ids,
                    format_func=lambda task_id: (
                        task_labels[task_id]
                    ),
                )

                target_id = st.selectbox(
                    "Target task",
                    options=task_ids,
                    format_func=lambda task_id: (
                        task_labels[task_id]
                    ),
                )

                add_connection_button = (
                    st.form_submit_button(
                        "Add Connection"
                    )
                )

            if add_connection_button:

                if source_id == target_id:

                    st.error(
                        "A task cannot connect to itself."
                    )

                elif any(
                    connection["source_id"] == source_id
                    and connection["target_id"] == target_id
                    for connection in connections
                ):

                    st.error(
                        "This connection already exists."
                    )

                elif would_create_cycle(
                    selected_workflow,
                    source_id,
                    target_id,
                ):

                    st.error(
                        "This connection would create "
                        "a circular path."
                    )

                else:

                    try:

                        add_connection(
                            workflow_id=workflow_id,
                            source_id=source_id,
                            target_id=target_id,
                        )

                        st.session_state.last_check = None

                        st.success(
                            "Connection saved successfully."
                        )

                        st.rerun()

                    except sqlite3.IntegrityError:

                        st.error(
                            "The connection could not be "
                            "saved. It may already exist."
                        )

                    except ValueError as error:

                        st.error(str(error))

        st.divider()

        # ------------------------------------------
        # Display saved connections
        # ------------------------------------------

        st.markdown("### Connections")

        # Reload the workflow to get the latest data.
        selected_workflow = load_workflow(
            workflow_id
        )

        connections = selected_workflow["connections"]

        if not connections:

            st.info(
                "No connections have been added yet."
            )

        else:

            for connection in connections:

                source_name = node_name(
                    selected_workflow,
                    connection["source_id"],
                )

                target_name = node_name(
                    selected_workflow,
                    connection["target_id"],
                )

                st.write(
                    f"{source_name} ➡️ {target_name}"
                )

        # ------------------------------------------
        # Visual graph
        # ------------------------------------------

        st.divider()

        st.markdown("### Workflow Graph")

        if not tasks:

            st.info(
                "Add tasks to display the graph."
            )

        else:

            dot_code = build_dot(selected_workflow)

            st.graphviz_chart(dot_code)

            with st.expander(
                "View Graphviz DOT description"
            ):

                st.code(
                    dot_code,
                    language="dot",
                )


# --------------------------------------------------
# 6. CHECK / RUN TAB
# --------------------------------------------------

with tab_check_run:

    st.header("Check and Run Workflow")

    if selected_workflow is None:

        st.info(
            "Select a workflow in the Workflows tab first."
        )

    else:

        workflow_id = selected_workflow["id"]

        st.write(
            f"Selected workflow: "
            f"**{selected_workflow['name']}**"
        )

        # ------------------------------------------
        # Check workflow structure
        # ------------------------------------------

        st.subheader("Check Workflow")

        st.write(
            "Check for basic structural problems "
            "before attempting execution."
        )

        if st.button(
            "Check Workflow",
            key="check_workflow_button",
        ):

            # Load the latest database version.
            current_workflow = load_workflow(
                workflow_id
            )

            errors = check_workflow(
                current_workflow
            )

            st.session_state.last_check = {
                "workflow_id": workflow_id,
                "errors": errors,
            }

        # Display the most recent Check result.
        last_check = st.session_state.last_check

        if (
            last_check is not None
            and last_check["workflow_id"] == workflow_id
        ):

            if last_check["errors"]:

                st.error(
                    "The workflow has problems "
                    "that should be corrected."
                )

                for error in last_check["errors"]:
                    st.write(f"- {error}")

            else:

                st.success(
                    "The basic structural checks passed."
                )

                st.write(
                    "This does not guarantee that every "
                    "task can execute successfully."
                )

        st.divider()

        # ------------------------------------------
        # Run workflow
        # ------------------------------------------

        st.subheader("Run Workflow")

        st.write(
            "The Run button is prepared for integration "
            "with Person 5's execution engine."
        )

        if st.button(
            "Run Workflow",
            key="run_workflow_button",
        ):

            st.info(
                "Execution is not connected yet. "
                "Person 5 must integrate the execution "
                "engine before this button can run tasks."
            )

            st.write(
                "No workflow was executed."
            )


# --------------------------------------------------
# 7. HISTORY TAB
# --------------------------------------------------

with tab_history:

    st.header("Workflow Execution History")

    if selected_workflow is None:

        st.info(
            "Select a workflow to view its history."
        )

    else:

        workflow_id = selected_workflow["id"]

        st.write(
            f"History for: "
            f"**{selected_workflow['name']}**"
        )

        history = get_history(workflow_id)

        if not history:

            st.info(
                "No execution history is available yet. "
                "History will appear after the execution "
                "engine records its results."
            )

        else:

            st.dataframe(
                history,
                use_container_width=True,
                hide_index=True,
            )