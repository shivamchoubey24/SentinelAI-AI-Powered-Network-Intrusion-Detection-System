"""Small data-access helpers used by the API, ETL and scripts."""
import json
from typing import Any, Dict, List

import pandas as pd
from sqlalchemy import func, select

from src.db.database import get_session, init_db
from src.db.models import Alert, Detection, ModelRun, SecurityLog

_CHUNK = 1000


def save_dataframe(df: pd.DataFrame, source: str) -> int:
    """Persist a DataFrame as SecurityLog rows. Returns rows written."""
    init_db()
    # JSON round-trip converts numpy/pandas scalars and NaN into plain types.
    records: List[Dict[str, Any]] = json.loads(df.to_json(orient="records"))
    written = 0
    with get_session() as s:
        for i in range(0, len(records), _CHUNK):
            chunk = records[i:i + _CHUNK]
            s.add_all(SecurityLog(source=source, payload=r) for r in chunk)
            written += len(chunk)
    return written


def record_model_run(info: Dict[str, Any]) -> int:
    init_db()
    m = info["metrics"]
    with get_session() as s:
        run = ModelRun(
            model_path=info["model_path"], dataset=info["dataset"],
            accuracy=m["accuracy"], precision=m["precision"],
            recall=m["recall"], f1_score=m["f1_score"],
            confusion_matrix=info["confusion_matrix"],
        )
        s.add(run)
        s.flush()
        return run.id


def latest_model_run() -> Dict[str, Any] | None:
    init_db()
    with get_session() as s:
        run = s.scalars(select(ModelRun).order_by(ModelRun.id.desc()).limit(1)).first()
        if run is None:
            return None
        return {
            "model_path": run.model_path, "trained_at": run.trained_at.isoformat(),
            "dataset": run.dataset,
            "metrics": {"accuracy": run.accuracy, "precision": run.precision,
                        "recall": run.recall, "f1_score": run.f1_score},
            "confusion_matrix": run.confusion_matrix,
        }


def record_detection(records: int, threats: int, model_path: str = "", client: str = "") -> int:
    init_db()
    with get_session() as s:
        d = Detection(records_analyzed=records, threats_detected=threats,
                      model_path=model_path, client=client)
        s.add(d)
        s.flush()
        return d.id


def create_alert(severity: str, threat_type: str, source_ip: str = "n/a", details: str = "") -> int:
    init_db()
    with get_session() as s:
        a = Alert(severity=severity, threat_type=threat_type, source_ip=source_ip, details=details)
        s.add(a)
        s.flush()
        return a.id


def recent_alerts(limit: int = 10) -> List[Dict[str, Any]]:
    init_db()
    with get_session() as s:
        rows = s.scalars(select(Alert).order_by(Alert.id.desc()).limit(limit)).all()
        return [{"timestamp": r.created_at.isoformat(), "threat_type": r.threat_type,
                 "severity": r.severity, "source_ip": r.source_ip, "status": r.status}
                for r in rows]


def summary() -> Dict[str, Any]:
    """Aggregate real counts from the database for the dashboard overview."""
    init_db()
    with get_session() as s:
        batches, records, threats = s.execute(
            select(func.count(Detection.id),
                   func.coalesce(func.sum(Detection.records_analyzed), 0),
                   func.coalesce(func.sum(Detection.threats_detected), 0))
        ).one()
        last = s.scalars(select(Detection.created_at).order_by(Detection.id.desc()).limit(1)).first()
        by_sev = dict(s.execute(select(Alert.severity, func.count(Alert.id)).group_by(Alert.severity)).all())
        open_alerts = s.scalar(select(func.count(Alert.id)).where(Alert.status == "open")) or 0
        total_alerts = s.scalar(select(func.count(Alert.id))) or 0
    return {
        "detection_batches": int(batches), "records_analyzed": int(records),
        "threats_detected": int(threats),
        "last_detection_at": last.isoformat() if last else None,
        "alerts_total": int(total_alerts), "alerts_open": int(open_alerts),
        "alerts_by_severity": {k: int(v) for k, v in by_sev.items()},
    }
