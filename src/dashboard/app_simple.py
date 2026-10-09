"""
SentinelAI dashboard (Phase 3).

Every number shown here comes from the SentinelAI API (which reads the
database, the trained model's evaluation metrics and the audit chain).
Nothing is simulated. When there is no data yet, the page says so.
"""
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.dashboard import auth  # noqa: E402
from src.dashboard.api_client import ApiError, SentinelClient  # noqa: E402

st.set_page_config(page_title="SentinelAI", page_icon="🛡️", layout="wide")

PAGES = ["Overview", "Threat Detection", "Model Performance", "Audit Log"]


def _client() -> SentinelClient:
    if "client" not in st.session_state:
        st.session_state.client = SentinelClient()
    return st.session_state.client


def login_gate() -> bool:
    """Return True when the visitor may see the dashboard."""
    if auth.auth_disabled():
        st.sidebar.warning("Dashboard login is DISABLED (development only).")
        return True
    if st.session_state.get("authed"):
        return True

    st.title("🛡️ SentinelAI")
    if not auth.is_configured():
        st.error("Dashboard login is not configured. Set DASHBOARD_PASSWORD "
                 "(or DASHBOARD_AUTH_DISABLED=true for local development).")
        return False

    failures = st.session_state.get("failed_logins", 0)
    with st.form("login"):
        pw = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")
    if submitted:
        import time
        delay = auth.backoff_seconds(failures)
        if delay:
            time.sleep(delay)
        if auth.check_password(pw):
            st.session_state.authed = True
            st.session_state.failed_logins = 0
            st.rerun()
        st.session_state.failed_logins = failures + 1
        st.error("Incorrect password.")
    return False


def _guard(fn):
    """Run a page; show API problems as readable messages instead of stack traces."""
    try:
        fn()
    except ApiError as e:
        if e.status in (401, 403):
            st.error(f"The dashboard's API key was rejected ({e}). Check SENTINEL_DASHBOARD_API_KEY.")
        elif e.status == 503:
            st.warning(str(e))
        else:
            st.error(str(e))


def page_overview():
    st.header("Overview")
    c = _client()
    health, status, summary = c.health(), c.status(), c.summary()

    a, b, d, e = st.columns(4)
    a.metric("API / database", health["status"].upper())
    b.metric("Audit chain", status["audit_chain"].upper())
    d.metric("Records analyzed", f"{summary['records_analyzed']:,}")
    e.metric("Threats detected", f"{summary['threats_detected']:,}")

    a, b, d = st.columns(3)
    a.metric("Open alerts", summary["alerts_open"])
    b.metric("Detection runs", summary["detection_batches"])
    d.metric("Model", "trained" if status["model"] == "trained" else "not trained")
    if summary["last_detection_at"]:
        st.caption(f"Last detection run: {summary['last_detection_at']}")
    else:
        st.info("No detection runs yet. Upload a CSV on the Threat Detection page.")

    sev = summary["alerts_by_severity"]
    if sev:
        order = [s for s in ("critical", "high", "medium", "low") if s in sev]
        fig = go.Figure(go.Bar(x=order, y=[sev[s] for s in order]))
        fig.update_layout(title="Alerts by severity", height=300, margin=dict(t=40, b=20))
        st.plotly_chart(fig, width="stretch")

    st.subheader("Recent alerts")
    alerts = c.threats(10)
    if alerts:
        st.dataframe(pd.DataFrame(alerts), width="stretch", hide_index=True)
    else:
        st.caption("No alerts recorded.")


def page_detection():
    st.header("Threat Detection")
    st.caption("Upload a CSV of preprocessed numeric feature rows (same columns the model was trained on). "
               "A trailing `label` column is ignored.")
    up = st.file_uploader("CSV file", type=["csv"])
    if up is None:
        return
    df = pd.read_csv(up)
    up.seek(0)
    st.write(f"{len(df):,} rows × {df.shape[1]} columns")
    with st.expander("Preview"):
        st.dataframe(df.head(10), width="stretch")
    if st.button("Analyze", type="primary"):
        with st.spinner("Running the trained model..."):
            res = _client().predict(up.name, up.getvalue())
        a, b, d = st.columns(3)
        a.metric("Records", f"{res['records_analyzed']:,}")
        b.metric("Flagged as attack", f"{res['threats_detected']:,}")
        d.metric("Attack share", f"{res['threat_percentage']}%")
        out = df.copy()
        out["prediction"] = ["attack" if p else "normal" for p in res["predictions"]]
        out["attack_probability"] = res["probabilities"]
        st.dataframe(out.sort_values("attack_probability", ascending=False).head(100),
                     width="stretch")
        st.download_button("Download results (CSV)", out.to_csv(index=False),
                           "sentinel_results.csv", "text/csv")


def _pct(v):
    return "n/a" if v is None else f"{v:.1%}"


def page_model():
    st.header("Model Performance")
    m = _client().metrics()
    if m.get("status") != "trained":
        st.info(m.get("message", "No trained model yet."))
        return

    st.subheader("Held-out test (NSL-KDD official KDDTest+) - the number to trust")
    ho = _client().held_out_metrics()
    if ho.get("status") != "evaluated":
        st.info(ho.get("message", "Run `python scripts/evaluate_model.py` for an honest, held-out score."))
    else:
        st.caption(ho.get("note", ""))
        tp, t21, at = ho["test_plus"], ho["test_21"], ho["attack_types"]
        a, b, c, d = st.columns(4)
        a.metric("Accuracy (held-out)", _pct(tp["accuracy"]), _pct(tp["accuracy"] - m["model_accuracy"]))
        b.metric("Recall (held-out)", _pct(tp["recall"]), _pct(tp["recall"] - m["recall"]))
        c.metric("False positive rate", _pct(tp["false_positive_rate"]))
        d.metric("KDDTest-21 accuracy", _pct(t21["accuracy"]))
        fam = {k: v for k, v in ho["per_family_recall"].items() if v.get("detection_rate") is not None}
        if fam:
            fig = go.Figure(go.Bar(x=[k.upper() for k in fam], y=[fam[k]["detection_rate"] for k in fam]))
            fig.update_layout(title="Detection rate by attack family (held-out)", yaxis_range=[0, 1], height=300)
            st.plotly_chart(fig, width="stretch")
        novel = at.get("novel_not_in_training", {})
        if novel.get("records"):
            st.warning(f"Attack types never seen in training ({novel['records']:,} records) are detected "
                      f"only {_pct(novel['detection_rate'])} of the time.")

    st.divider()
    st.subheader("Training-split metrics (optimistic)")
    st.caption(f"Trained {m['trained_at']} on `{m['dataset']}`. Scored on a random 20% split of the same "
              "file it trained on, so it overstates real-world performance - see the held-out numbers above.")
    a, b, c, d = st.columns(4)
    a.metric("Accuracy", _pct(m["model_accuracy"]))
    b.metric("Precision", _pct(m["precision"]))
    c.metric("Recall", _pct(m["recall"]))
    d.metric("F1", _pct(m["f1_score"]))
    cm = m["confusion_matrix"]
    fig = go.Figure(go.Heatmap(z=cm, x=["Pred normal", "Pred attack"], y=["Actual normal", "Actual attack"],
                               text=cm, texttemplate="%{text}", colorscale="Blues", showscale=False))
    fig.update_layout(title="Confusion matrix (training-split test)", height=340, yaxis_autorange="reversed")
    st.plotly_chart(fig, width="stretch")


def page_audit():
    st.header("Audit Log")
    st.caption("Single-node hash-chained log. It detects edits to past entries; it is not a distributed ledger.")
    c = _client()
    v = c.audit_verify()
    if v["valid"]:
        st.success(f"Chain valid · {v['length']} blocks · {v.get('checkpoints_checked', 0)} checkpoints cross-checked")
    else:
        st.error(f"Chain INVALID: {v.get('error')} (block {v.get('bad_index')})")
    st.code(f"head: {v.get('head_hash')}")
    blocks = c.audit_blocks(25)
    if blocks:
        df = pd.DataFrame(blocks)
        df["hash"] = df["hash"].str[:16] + "…"
        df["previous_hash"] = df["previous_hash"].str[:16] + "…"
        st.dataframe(df, width="stretch", hide_index=True)


def main():
    if not login_gate():
        return
    st.sidebar.title("🛡️ SentinelAI")
    page = st.sidebar.radio("Navigate", PAGES)
    if st.sidebar.button("Refresh"):
        st.rerun()
    if not auth.auth_disabled() and st.sidebar.button("Sign out"):
        st.session_state.authed = False
        st.rerun()
    routes = {"Overview": page_overview, "Threat Detection": page_detection,
              "Model Performance": page_model, "Audit Log": page_audit}
    _guard(routes[page])


if __name__ == "__main__":
    main()
