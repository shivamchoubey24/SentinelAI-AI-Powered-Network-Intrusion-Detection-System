"""
FastAPI backend for SentinelAI (Phase 2).

Adds to Phase 1: database persistence, API-key auth with roles, locked-down
CORS, input validation, rate limiting, Prometheus metrics and an honest
audit-chain verification endpoint.
"""

import hashlib
import io
import json
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd
from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.api import metrics as m  # noqa: E402
from src.blockchain.blockchain_logger import BlockchainLogger  # noqa: E402
from src.db import init_db, repository  # noqa: E402
from src.security.auth import Principal, auth_disabled, require_role  # noqa: E402
from src.security.rate_limit import RateLimiter  # noqa: E402
from src.utils.config_loader import ConfigLoader  # noqa: E402
from src.utils.logger import setup_logger  # noqa: E402

logger = setup_logger(__name__)

LATEST_MODEL_INFO_PATH = Path("data/models/latest.json")
EVALUATION_PATH = Path("data/models/evaluation.json")
_model_cache = {"model": None, "info": None}

_config = ConfigLoader.load_config()
_api_cfg = _config.get("api", {})
_limits = _config.get("performance", {}).get("limits", {})


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


MAX_UPLOAD_BYTES = _env_int("MAX_UPLOAD_BYTES", 10 * 1024 * 1024)
MAX_ROWS = _env_int("MAX_BATCH_ROWS", int(_limits.get("max_batch_size", 10000)))
RATE_LIMIT = _env_int("RATE_LIMIT_PER_MINUTE", int(_api_cfg.get("rate_limit", 100)))
limiter = RateLimiter(limit=RATE_LIMIT, window_seconds=60)


def _cors_origins() -> List[str]:
    env = os.environ.get("CORS_ORIGINS")
    origins = [o.strip() for o in env.split(",")] if env else list(_api_cfg.get("cors_origins", []))
    return [o for o in origins if o and o != "*"]  # never allow wildcard


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    if auth_disabled():
        logger.warning("SENTINEL_AUTH_DISABLED is set - API authentication is OFF (development only)")
    yield


app = FastAPI(
    title="SentinelAI API",
    description="AI-powered network intrusion detection API",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=False,          # API keys travel in a header, not cookies
    allow_methods=["GET", "POST"],
    allow_headers=["X-API-Key", "Content-Type"],
)


def _route_template(request: Request) -> str:
    route = request.scope.get("route")
    return getattr(route, "path", "unmatched")


@app.middleware("http")
async def rate_limit_and_metrics(request: Request, call_next):
    path = request.url.path
    if path != "/health":
        key = request.headers.get("x-api-key")
        identity = f"key:{hashlib.sha256(key.encode()).hexdigest()[:16]}" if key else f"ip:{request.client.host if request.client else 'unknown'}"
        allowed, retry_after = limiter.check(identity)
        if not allowed:
            m.RATE_LIMITED.inc()
            return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429,
                                headers={"Retry-After": str(retry_after)})
    start = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        tpl = _route_template(request)
        m.REQUESTS.labels(request.method, tpl, str(status_code)).inc()
        m.LATENCY.labels(request.method, tpl).observe(time.perf_counter() - start)


class ThreatAlert(BaseModel):
    timestamp: str
    threat_type: str
    severity: str
    source_ip: str
    status: str


def _load_latest_model():
    """Lazily load the newest trained model. Returns (model, info) or (None, None)."""
    if _model_cache["model"] is not None:
        return _model_cache["model"], _model_cache["info"]
    if not LATEST_MODEL_INFO_PATH.exists():
        return None, None
    with open(LATEST_MODEL_INFO_PATH) as f:
        info = json.load(f)
    try:
        from src.models.threat_detector import MLPGRUModel  # heavy (TensorFlow) - import on demand
        wrapper = MLPGRUModel(ConfigLoader.load_config())
        wrapper.load_model(info["model_path"])
    except Exception as e:
        logger.error(f"Failed to load model from {info.get('model_path')}: {e}")
        return None, None
    _model_cache.update(model=wrapper, info=info)
    m.MODEL_LOADED.set(1)
    return wrapper, info


def _read_model_info():
    """Model metadata without loading TensorFlow: latest.json first, then the DB."""
    if LATEST_MODEL_INFO_PATH.exists():
        with open(LATEST_MODEL_INFO_PATH) as f:
            return json.load(f)
    return repository.latest_model_run()


def _severity(max_prob: float) -> str:
    levels = _config.get("threat_detection", {}).get("severity_levels", {})
    for name in ("critical", "high", "medium", "low"):
        if max_prob >= float(levels.get(name, {"critical": .9, "high": .7, "medium": .5, "low": .3}[name])):
            return name
    return "low"


# ---------------------------------------------------------------- endpoints
@app.get("/health")
async def health():
    """Liveness/readiness probe (unauthenticated, no sensitive data)."""
    try:
        repository.recent_alerts(1)
        db = "ok"
    except Exception:
        db = "unavailable"
    return {"status": "ok" if db == "ok" else "degraded", "database": db}


@app.get("/")
async def root():
    return {"message": "SentinelAI API", "version": app.version, "docs": "/docs"}


@app.get("/metrics", include_in_schema=False)
async def prometheus_metrics(request: Request):
    """Prometheus scrape endpoint. Needs a viewer key unless METRICS_PUBLIC=true."""
    if os.environ.get("METRICS_PUBLIC", "").lower() not in ("1", "true", "yes"):
        require_role("viewer")(request, request.headers.get("x-api-key"))
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/v1/status")
async def get_status(_: Principal = Depends(require_role("viewer"))):
    info = _read_model_info()
    verification = BlockchainLogger().verify()
    m.AUDIT_CHAIN_VALID.set(1 if verification["valid"] else 0)
    return {
        "system": "operational",
        "audit_chain": "valid" if verification["valid"] else "INVALID",
        "model": "trained" if info else "not_trained",
        "model_trained_at": info["trained_at"] if info else None,
    }


@app.get("/api/v1/audit/verify")
async def audit_verify(_: Principal = Depends(require_role("viewer"))):
    """Verify the hash-chained audit log and cross-check saved checkpoints."""
    result = BlockchainLogger().verify()
    m.AUDIT_CHAIN_VALID.set(1 if result["valid"] else 0)
    return result


@app.post("/api/v1/audit/checkpoint")
async def audit_checkpoint(_: Principal = Depends(require_role("admin"))):
    """Record the current (length, head hash). Copy checkpoints.jsonl somewhere write-protected."""
    return BlockchainLogger().create_checkpoint()


@app.post("/api/v1/audit/anchor")
def audit_anchor(_: Principal = Depends(require_role("admin"))):
    """Publish the audit chain's head hash on a public Ethereum testnet (opt-in, admin only)."""
    from src.blockchain import anchor
    if not anchor.is_configured():
        raise HTTPException(status_code=501,
                            detail="Anchoring is not configured (set ANCHOR_RPC_URL and ANCHOR_PRIVATE_KEY)")
    try:
        return anchor.anchor_head(BlockchainLogger())
    except anchor.AnchorError as e:
        logger.error(f"Anchoring failed: {e}")
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/v1/audit/anchors")
def audit_anchors(verify: bool = False, _: Principal = Depends(require_role("viewer"))):
    """List recorded anchors; with ?verify=true compare them to the public chain (needs ANCHOR_RPC_URL)."""
    from src.blockchain import anchor
    audit_logger = BlockchainLogger()
    records = anchor.read_anchors(audit_logger)
    if not verify:
        return {"anchors": records, "verified": None}
    if not os.environ.get("ANCHOR_RPC_URL"):
        raise HTTPException(status_code=501, detail="Verification needs ANCHOR_RPC_URL")
    try:
        return {"anchors": records, "verified": anchor.verify_anchors(audit_logger)}
    except anchor.AnchorError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/v1/summary")
async def get_summary(_: Principal = Depends(require_role("viewer"))):
    """Real aggregate counts (detections, threats, alerts) from the database."""
    try:
        return repository.summary()
    except Exception as e:
        logger.error(f"Error building summary: {e}")
        raise HTTPException(status_code=500, detail="Could not build summary")


@app.get("/api/v1/audit/blocks")
async def audit_blocks(limit: int = Query(10, ge=1, le=100),
                       _: Principal = Depends(require_role("viewer"))):
    """Most recent audit-chain blocks (newest first), hashes shortened for display."""
    chain = BlockchainLogger().blockchain.get_chain()
    blocks = chain[-limit:][::-1]
    return [{"index": b["index"], "timestamp": b["timestamp"],
             "event_type": b["data"].get("type", "GENESIS") if isinstance(b["data"], dict) else "GENESIS",
             "hash": b["hash"], "previous_hash": b["previous_hash"]} for b in blocks]


@app.get("/api/v1/threats", response_model=List[ThreatAlert])
async def get_threats(limit: int = Query(10, ge=1, le=100),
                      _: Principal = Depends(require_role("viewer"))):
    """Recent alerts raised by real detection runs (stored in the database)."""
    try:
        return [ThreatAlert(**a) for a in repository.recent_alerts(limit)]
    except Exception as e:
        logger.error(f"Error reading alerts: {e}")
        raise HTTPException(status_code=500, detail="Could not read alerts")


@app.get("/api/v1/metrics")
async def get_metrics(_: Principal = Depends(require_role("viewer"))):
    """Evaluation metrics from the last real training run."""
    info = _read_model_info()
    if info is None:
        return {"status": "not_trained",
                "message": "No trained model found. Run scripts/train_model.py first."}
    held_out = None
    if EVALUATION_PATH.exists():
        try:
            held_out = json.loads(EVALUATION_PATH.read_text())
            if held_out.get("model_path") != info.get("model_path"):
                held_out = None  # stale: it was computed for a different model
        except (OSError, ValueError):
            held_out = None
    return {
        "status": "trained",
        "held_out_evaluation": held_out,
        "trained_at": info["trained_at"],
        "dataset": info["dataset"],
        "model_accuracy": info["metrics"]["accuracy"],
        "precision": info["metrics"]["precision"],
        "recall": info["metrics"]["recall"],
        "f1_score": info["metrics"]["f1_score"],
        "confusion_matrix": info["confusion_matrix"],
    }


@app.get("/api/v1/metrics/held-out")
async def get_held_out_metrics(_: Principal = Depends(require_role("viewer"))):
    """
    Metrics from scripts/evaluate_model.py on NSL-KDD's official held-out
    KDDTest+ set. Unlike /api/v1/metrics (a random split of the training
    file), this set includes attack types the model never trained on, so
    it is a more honest estimate of real-world performance.
    """
    path = Path("data/models/latest_eval.json")
    if not path.exists():
        return {"status": "not_evaluated",
                "message": "Run scripts/evaluate_model.py to generate held-out metrics."}
    with open(path) as f:
        data = json.load(f)
    return {"status": "evaluated", **data}


async def _read_upload(file: UploadFile) -> bytes:
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=415, detail="Upload must be a .csv file")
    buf = bytearray()
    while chunk := await file.read(64 * 1024):
        buf.extend(chunk)
        if len(buf) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail=f"File exceeds {MAX_UPLOAD_BYTES} bytes")
    if not buf:
        raise HTTPException(status_code=400, detail="Empty file")
    return bytes(buf)


def _validate_features(df: pd.DataFrame, model_wrapper) -> np.ndarray:
    if df.empty:
        raise HTTPException(status_code=422, detail="CSV contains no rows")
    if len(df) > MAX_ROWS:
        raise HTTPException(status_code=413, detail=f"At most {MAX_ROWS} rows per request")
    if df.shape[1] > 1 and str(df.columns[-1]).lower() in ("label", "class"):
        df = df.iloc[:, :-1]
    try:
        values = df.astype(float).to_numpy()
    except (ValueError, TypeError):
        raise HTTPException(status_code=422, detail="All feature columns must be numeric (or boolean)")
    if not np.isfinite(values).all():
        raise HTTPException(status_code=422, detail="Features contain NaN or infinite values")
    expected = getattr(getattr(model_wrapper, "scaler", None), "n_features_in_", None)
    if expected is not None and values.shape[1] != expected:
        raise HTTPException(status_code=422,
                            detail=f"Expected {expected} feature columns, got {values.shape[1]}")
    return values


@app.post("/api/v1/predict")
async def predict(file: UploadFile = File(...),
                  principal: Principal = Depends(require_role("analyst"))):
    """Run the trained model on an uploaded CSV of preprocessed numeric feature rows."""
    model_wrapper, info = _load_latest_model()
    if model_wrapper is None:
        raise HTTPException(status_code=503,
                            detail="No trained model available. Run scripts/train_model.py first.")

    raw = await _read_upload(file)
    try:
        df = pd.read_csv(io.BytesIO(raw))
    except Exception:
        raise HTTPException(status_code=400, detail="Could not parse CSV")
    values = _validate_features(df, model_wrapper)

    try:
        predictions, probabilities = model_wrapper.predict(values)
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=400, detail="Prediction failed for the uploaded data")

    probs = np.asarray(probabilities, dtype=float).flatten()
    n, threats = len(df), int(np.asarray(predictions).sum())
    m.PREDICTIONS.inc(n)
    m.THREATS.inc(threats)

    # Persist the detection and (if any attacks) an alert; audit-log the run.
    try:
        repository.record_detection(n, threats, info.get("model_path", ""), principal.name)
        if threats:
            repository.create_alert(
                severity=_severity(float(probs.max())), threat_type="batch_intrusion_detected",
                details=f"{threats}/{n} records classified as attack by {principal.name}'s upload")
    except Exception as e:
        logger.warning(f"Could not persist detection: {e}")
    BlockchainLogger().log_threat_detection({
        "threat_type": "batch_prediction", "severity": "info", "source_ip": "n/a",
        "status": "analyzed", "records_analyzed": n, "threats_detected": threats,
        "client": principal.name,
    })

    return {
        "records_analyzed": n,
        "threats_detected": threats,
        "threat_percentage": round(threats / n * 100, 2) if n else 0,
        "predictions": np.asarray(predictions).tolist(),
        "probabilities": probs.tolist(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.environ.get("API_HOST", "127.0.0.1"), port=int(os.environ.get("API_PORT", 8000)))
