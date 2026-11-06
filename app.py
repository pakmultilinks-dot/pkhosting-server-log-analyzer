"""PKHosting Server Log Analyzer.

Upload web server or application error logs and get a plain language
summary of what went wrong, grouped by problem type, with likely causes
and suggested fixes. All test logs are generated, never real customer logs.
"""

import io
import os

import pandas as pd
import streamlit as st

from logparser import CAUSES_FIXES, LABELS, parse_log, plain_summary

st.set_page_config(page_title="PKHosting Server Log Analyzer", layout="wide")
st.title("PKHosting Server Log Analyzer")
st.write(
    "Upload a web server or application error log and see, in plain "
    "language, what went wrong, how often, and what to fix first. "
    "No log leaves your browser session, and no real customer logs "
    "are used anywhere in this tool."
)

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "sample_logs")


def _load_sample(name):
    with open(os.path.join(SAMPLE_DIR, name), encoding="utf-8") as fh:
        return fh.read()


def _show_result(result, source_name):
    st.subheader("Summary: %s" % source_name)
    st.write(plain_summary(result))
    counts = result["problem_counts"]
    if counts:
        chart = pd.DataFrame(
            {"problem": [LABELS[k] for k in counts], "lines": list(counts.values())}
        ).set_index("problem")
        st.bar_chart(chart)
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Grouped by problem type")
        rows = [
            {
                "Problem type": LABELS[k],
                "Lines": v,
                "Likely cause": CAUSES_FIXES[k][0],
                "Suggested fix": CAUSES_FIXES[k][1],
            }
            for k, v in sorted(counts.items(), key=lambda kv: -kv[1])
        ]
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True)
        else:
            st.write("No problems found in this log.")
    with col2:
        st.subheader("Top URLs")
        if result["top_urls"]:
            st.dataframe(
                pd.DataFrame(result["top_urls"], columns=["URL", "Requests"]),
                use_container_width=True,
            )
        else:
            st.write("No URLs in this log.")
        st.subheader("Top IPs")
        if result["top_ips"]:
            st.dataframe(
                pd.DataFrame(result["top_ips"], columns=["IP", "Requests"]),
                use_container_width=True,
            )
        else:
            st.write("No IPs in this log.")
    st.subheader("Line by line")
    table = pd.DataFrame(
        [
            {
                "Line": r["line_no"],
                "Format": r["format"],
                "IP": r["ip"],
                "URL": r["url"],
                "Status": r["status"],
                "Level": r["level"],
                "Problem type": LABELS[r["problem_type"]],
                "Log line": r["raw"],
            }
            for r in result["records"]
        ]
    )
    st.dataframe(table, use_container_width=True)
    st.download_button(
        "Download line by line table (CSV)",
        data=table.to_csv(index=False).encode("utf-8"),
        file_name="log-analysis.csv",
        mime="text/csv",
    )


samples = sorted(os.listdir(SAMPLE_DIR)) if os.path.isdir(SAMPLE_DIR) else []
choice = st.selectbox(
    "Try a built-in sample log, no upload needed",
    ["(choose a sample)"] + samples,
)
if choice != "(choose a sample)":
    _show_result(parse_log(_load_sample(choice)), choice)

st.subheader("Upload your own log")
uploads = st.file_uploader(
    "Upload one or more log files (Nginx or Apache access and error logs, "
    "or application logs)",
    type=["log", "txt"],
    accept_multiple_files=True,
)
if uploads:
    for up in uploads:
        text = up.read().decode("utf-8", errors="replace")
        _show_result(parse_log(text), up.name)

with st.expander("What formats are supported?"):
    st.write(
        "Format A, Nginx or Apache combined access log, example: "
        '203.0.113.10 - - [05/Oct/2026:13:55:36 +0500] "GET /shop HTTP/1.1" '
        '200 5123 "-" "Mozilla/5.0" 0.412'
    )
    st.write(
        "Format A, Nginx error log, example: 2026/10/05 13:55:36 [error] "
        "123#0: *45 connect() failed (111: Connection refused) while "
        "connecting to upstream, client: 203.0.113.10"
    )
    st.write(
        "Format B, application log, example: 2026-10-05 13:55:36,123 ERROR "
        "app.db: connection to database failed: could not connect to server"
    )
    st.write(
        "Lines are grouped into 404 not found, 500 server error, 502, 503 "
        "or 504 upstream or timeout, slow request, database connection "
        "error, PHP or application exception, authentication failure, "
        "SSL or TLS error, file not found or permission error, rate limit "
        "429, bot or crawler flood, and unknown or other."
    )
