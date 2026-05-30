import requests
import streamlit as st
from pathlib import Path
import json


st.set_page_config(page_title="KPN Agent Demo", page_icon="📡", layout="wide")

st.title("KPN Agent Demo")
st.caption("Simple UI for your FastAPI agent endpoints")

with st.sidebar:
    st.header("Connection")
    api_base = st.text_input("API Base URL", value="http://127.0.0.1:8000")
    timeout_sec = st.number_input("Timeout (seconds)", min_value=5, max_value=120, value=60)

st.subheader("Health Check")
if st.button("Check API Health"):
    try:
        resp = requests.get(f"{api_base.rstrip('/')}/health", timeout=int(timeout_sec))
        resp.raise_for_status()
        st.success(f"API is healthy: {resp.json()}")
    except Exception as exc:
        st.error(f"Health check failed: {exc}")

st.divider()
st.subheader("Ask A Question")

sample_questions = [
    "What are the latest KPN announcements?",
    "What do the quarterly reports say about performance?",
    "Compare quarterly performance and recent launches",
    "Summarize recent news and financial highlights",
]

default_query = "What are the latest KPN announcements?"
if "query_text" not in st.session_state:
    st.session_state.query_text = default_query

chosen_sample = st.selectbox("Sample questions", options=sample_questions, index=0)
if st.button("Use selected sample"):
    st.session_state.query_text = chosen_sample

query = st.text_area("Question", key="query_text", height=100)

col1, col2, col3 = st.columns(3)
with col1:
    top_k = st.slider("top_k", min_value=1, max_value=10, value=4)
with col2:
    max_tool_rounds = st.slider("max_tool_rounds", min_value=1, max_value=5, value=2)
with col3:
    disable_log = st.checkbox("disable_log", value=False)

if st.button("Run Query", type="primary"):
    payload = {
        "query": query,
        "top_k": int(top_k),
        "max_tool_rounds": int(max_tool_rounds),
        "disable_log": bool(disable_log),
    }

    with st.spinner("Querying agent..."):
        try:
            resp = requests.post(
                f"{api_base.rstrip('/')}/query",
                json=payload,
                timeout=int(timeout_sec),
            )

            if resp.status_code >= 400:
                st.error(f"API error {resp.status_code}: {resp.text}")
            else:
                data = resp.json()
                st.success("Query completed")

                st.markdown("### Answer")
                st.write(data.get("answer", ""))

                st.markdown("### Meta")
                st.json(
                    {
                        "run_id": data.get("run_id"),
                        "selected_tools": data.get("selected_tools", []),
                        "run_log_path": data.get("run_log_path", ""),
                    }
                )

                st.markdown("### Citations")
                citations = data.get("citations", [])
                if not citations:
                    st.info("No citations returned.")
                else:
                    for idx, item in enumerate(citations, start=1):
                        with st.expander(f"{idx}. {item.get('title', 'Untitled source')}"):
                            st.write(f"Tool: {item.get('tool_name', '')}")
                            st.write(f"Source type: {item.get('source_type', '')}")
                            st.write(f"URL: {item.get('url', '')}")
                            st.write(f"Score: {item.get('score', '')}")
                            st.write(item.get("snippet", ""))

                run_log_path = data.get("run_log_path", "")
                st.markdown("### Observability")
                if not run_log_path:
                    st.info("No run log path returned by API.")
                else:
                    st.write(f"Run log path: {run_log_path}")
                    log_file = Path(run_log_path)
                    if not log_file.exists():
                        st.warning("Run log file not found from this Streamlit process.")
                    else:
                        try:
                            run_log = log_file.read_text(encoding="utf-8")
                            run_data = json.loads(run_log)
                        except Exception as exc:
                            st.error(f"Could not read run log: {exc}")
                            run_data = {}

                        if run_data:
                            planner_steps = run_data.get("planner_steps", [])
                            tool_traces = run_data.get("tool_traces", [])

                            with st.expander("Planner steps", expanded=False):
                                st.json(planner_steps)

                            with st.expander("Tool traces", expanded=True):
                                for idx, trace in enumerate(tool_traces, start=1):
                                    st.markdown(
                                        f"**{idx}. {trace.get('tool_name', '')}** "
                                        f"(status={trace.get('status', '')}, rows={trace.get('returned_rows', 0)}, "
                                        f"latency_ms={trace.get('latency_ms', 0)})"
                                    )
                                    rows = trace.get("rows", []) or []
                                    if rows:
                                        st.dataframe(rows)
                                    else:
                                        st.write("No rows for this tool call.")

        except Exception as exc:
            st.error(f"Request failed: {exc}")
