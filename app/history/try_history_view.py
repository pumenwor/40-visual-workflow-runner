import streamlit as st

from history_view import render_history
from sample_runs import runs
from sample_workflow import workflow

st.title("Testing my History tab")

render_history(workflow, runs)