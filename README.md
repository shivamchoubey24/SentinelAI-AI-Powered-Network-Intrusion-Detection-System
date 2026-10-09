# SentinelAI — AI-Powered Network Intrusion Detection

SentinelAI trains a hybrid MLP-GRU model on the NSL-KDD intrusion-detection
benchmark, serves it behind an authenticated FastAPI backend, records every
detection and training run in a real database and a tamper-evident audit
log, and exposes a Streamlit dashboard for analysts.

This README describes the project as it stands: what is real, what its
numbers actually mean, and what its limits are.

## Contents

- [Quick start](#quick-start)
- [Architecture](#architecture)
- [Setup without Docker](#setup-without-docker)
- [Training and evaluating the model](#training-and-evaluating-the-model)
- [API reference](#api-reference)
- [Dashboard](#dashboard)
- [Security](#security)
- [Audit log](#audit-log)
- [Database](#database)
- [Monitoring](#monitoring)
- [Testing and CI](#testing-and-ci)
- [Honest evaluation results](#honest-evaluation-results)
- [Known limitations](#known-limitations)
- [Project layout](#project-layout)

## Quick start

```bash
cp config/.env.example config/.env
# edit config/.env: set SENTINEL_API_KEYS, DASHBOARD_PASSWORD, SENTINEL_DASHBOARD_API_KEY

docker compose up --build
# API:       http://localhost:8000/docs
# Dashboard: http://localhost:8501
```

The API refuses every protected request until `SENTINEL_API_KEYS` is set
(fail closed). Generate keys with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

`SENTINEL_API_KEYS` is a comma-separated list of `name:key:role`, where role
is `viewer`, `analyst`, or `admin` (each includes the roles below it). Give
the dashboard's own key `analyst` (it needs to upload files for detection).

No model is trained yet at this point — `/api/v1/predict` returns 503 until
you train one (see below).

## Architecture

```
                    ┌─────────────┐
   CSV upload  ───▶ │  FastAPI    │──▶ SQLite / PostgreSQL (security_logs,
                    │  (src/api)  │    model_runs, detections, alerts)
                    │             │
                    │             │──▶ hash-chained audit log (JSON,
                    │             │    file-locked, optional testnet anchor)
                    │             │
                    │             │──▶ MLP-GRU model (Keras .h5 + JSON
                    │             │    preprocessing, no pickle)
                    └─────┬───────┘
                          │ HTTP + X-API-Key
                    ┌─────▼───────┐
                    │  Streamlit  │  password-gated, reads everything
                    │  dashboard  │  through the API — no direct DB/file
                    └─────────────┘  access, no simulated numbers
```

The dashboard is a thin client. It never touches the database, model files,
or audit log directly — every number it shows came back from an API call,
so what you see in the browser is what the API would give any other client.

## Setup without Docker

Requires Python 3.12.

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt        # or: sed 's/^tensorflow>=/tensorflow-cpu>=/' requirements.txt | pip install -r /dev/stdin

cp config/.env.example config/.env     # edit as above
export $(grep -v '^#' config/.env | xargs)   # or use python-dotenv / direnv

python scripts/init_database.py        # creates data/ dirs + DB schema
python scripts/download_datasets.py    # fetches NSL-KDD (KDDTrain+_20Percent, KDDTest+)
python scripts/train_model.py          # trains, writes data/models/latest.json
python scripts/evaluate_model.py       # honest held-out score, see below

python -m src.api.main                 # API on :8000
streamlit run src/dashboard/app_simple.py   # dashboard on :8501, separate shell
```

## Training and evaluating the model

`scripts/train_model.py` trains on `data/processed/nsl_kdd_processed.csv`
(NSL-KDD's `KDDTrain+_20Percent.txt`, one-hot encoded, with a random 20%
held out for its reported metrics) and writes:

- `data/models/<timestamp>_model.h5` — the Keras model
- `data/models/<timestamp>_preproc.json` — the fitted `StandardScaler` and
  `LabelEncoder` state, plus a SHA-256 of the model file
- `data/models/latest.json` — pointer + metrics the API/dashboard read

**These training-split metrics are optimistic.** They come from a random
split of the same file the model trained on, so easy and hard examples of
the same attack type appear on both sides of the split. `scripts/evaluate_model.py`
scores the model instead on NSL-KDD's official held-out `KDDTest+` file,
which contains attack types the model never saw during training. Run it
after training:

```bash
python scripts/evaluate_model.py
```

This writes `data/models/latest_eval.json`, served at
`GET /api/v1/metrics/held-out` and shown on the dashboard's Model
Performance page under "Held-out test — the number to trust". See
[Honest evaluation results](#honest-evaluation-results) for what it found on
the model shipped with this repository.

### Model artifacts are not pickled

Earlier versions of this project pickled the scaler and label encoder.
Unpickling executes arbitrary code, so a malicious `.pkl` file is a code
execution vector, not just bad data. `save_model`/`load_model` now write and
read plain JSON. `load_model` refuses old `.pkl` artifacts unless
`SENTINEL_ALLOW_LEGACY_PICKLE=true` is set. To convert existing models once:

```bash
python scripts/migrate_model_artifacts.py           # keeps the .pkl files
python scripts/migrate_model_artifacts.py --delete   # removes them after converting
```

The Keras `.h5` file itself is still not cryptographically verified beyond
the SHA-256 hash check at load time (which only catches accidental or
in-place tampering, not a swapped-in malicious file) — see
[Known limitations](#known-limitations).

## API reference

All endpoints except `/health` require an `X-API-Key` header. Interactive
docs at `/docs` once the server is running.

| Method | Path | Role | Purpose |
|---|---|---|---|
| GET | `/health` | none | Liveness/readiness probe |
| GET | `/api/v1/status` | viewer | System, model, and audit-chain status |
| GET | `/api/v1/summary` | viewer | Real aggregate counts (detections, threats, alerts) |
| GET | `/api/v1/threats` | viewer | Recent alerts (`?limit=`) |
| GET | `/api/v1/metrics` | viewer | Training-split model metrics |
| GET | `/api/v1/metrics/held-out` | viewer | Held-out `KDDTest+` evaluation (see above) |
| POST | `/api/v1/predict` | analyst | Run the model on an uploaded CSV |
| GET | `/api/v1/audit/verify` | viewer | Verify the audit chain + checkpoints |
| GET | `/api/v1/audit/blocks` | viewer | Recent audit-log entries (`?limit=`) |
| POST | `/api/v1/audit/checkpoint` | admin | Record a local checkpoint |
| POST | `/api/v1/audit/anchor` | admin | Publish the chain head on a public testnet (opt-in, see below) |
| GET | `/api/v1/audit/anchors` | viewer | List/verify testnet anchors (`?verify=true`) |
| GET | `/metrics` | viewer* | Prometheus metrics (`METRICS_PUBLIC=true` to expose without a key) |

`/api/v1/predict` accepts a CSV of preprocessed numeric feature rows (same
columns the model trained on; a trailing `label`/`class` column is dropped
if present). Uploads are size-, row-, and column-count-bounded
(`MAX_UPLOAD_BYTES`, `MAX_BATCH_ROWS`), and non-numeric or non-finite values
are rejected before they reach the model.

## Dashboard

`streamlit run src/dashboard/app_simple.py` (or `app.py`, kept as a
compatibility shim). Pages: Overview, Threat Detection, Model Performance,
Audit Log.

Configuration:

- `DASHBOARD_PASSWORD` — required; with none set, the login page refuses
  everyone rather than defaulting open. `DASHBOARD_AUTH_DISABLED=true` skips
  the login for local development only.
- `SENTINEL_DASHBOARD_API_KEY` — the dashboard's own API key, needs
  `analyst` role for uploads.
- `SENTINEL_API_URL` — where the dashboard finds the API (docker-compose
  sets this to `http://api:8000` automatically).

Every number on every page — including the confusion matrix, alert
severities, and audit-chain blocks — is read from the API at render time.
There is no session-local counter, no random walk, and no hardcoded demo
figure anywhere in the dashboard source (`tests/test_dashboard.py` checks
for this directly).

## Security

- **Authentication**: API-key based, roles `viewer < analyst < admin`, keys
  compared with `hmac.compare_digest` against SHA-256 digests (not stored or
  compared in plaintext). With no keys configured, every protected endpoint
  returns 503 rather than silently allowing access.
- **CORS**: origins come from `CORS_ORIGINS` (or `api.cors_origins` in
  `config/config.yaml`); a wildcard is never honored even if set.
- **Rate limiting**: per-process, keyed by API key (or client IP if none is
  given), configurable via `RATE_LIMIT_PER_MINUTE`. Per-process means it
  multiplies across multiple workers/replicas — see limitations.
- **Input validation**: upload size, row count, and column count are
  bounded; feature values must be numeric and finite.
- **No pickle for model artifacts** (see above); pickle is still used for
  reading pre-Phase-2 audit-chain files, through a restricted unpickler that
  only accepts the one expected class.

## Audit log

`src/blockchain/blockchain_logger.py` is an honestly-named single-node
hash-chained log, not a distributed ledger. Each entry hashes in the
previous entry's hash; `GET /api/v1/audit/verify` re-walks the whole chain
and cross-checks it against periodic local checkpoints written to
`checkpoints.jsonl`, which catches truncation (deleting recent entries) as
well as tampering with old ones. Writes are file-locked (`fcntl`) so
multiple API workers don't corrupt the chain, and use atomic JSON saves. A
Phase-1 `.pkl` chain file, if present, migrates automatically on first load.

**What local verification cannot catch**: someone with write access to
*both* the chain file and `checkpoints.jsonl` can rewrite history and
recompute both consistently. Local checks alone cannot distinguish that from
genuine history.

### Optional: anchoring to a public testnet

`src/blockchain/anchor.py` addresses the limitation above by publishing
`(chain length, head hash)` as a zero-value transaction on a public Ethereum
testnet — a record outside the operator's control. Configure:

```bash
ANCHOR_RPC_URL=https://<your-testnet-provider-url>
ANCHOR_PRIVATE_KEY=0x...        # a funded TESTNET account; never mainnet by default
```

Then `POST /api/v1/audit/anchor` (admin) to anchor, and
`GET /api/v1/audit/anchors?verify=true` (viewer) to check recorded anchors
against the public chain. Anchoring to Ethereum mainnet is refused unless
`ANCHOR_ALLOW_MAINNET=true` is explicitly set (mainnet transactions cost
real money). This proves the log's head existed no later than the anchoring
block and was not rewritten since — it says nothing about whether entries
were truthful when written, and it requires a funded wallet and an RPC
provider you control. Tested against an in-memory Ethereum chain
(`tests/test_anchor.py`); never run against a live testnet by this project.

## Database

SQLAlchemy 2, SQLite by default (`data/sentinel.db`), PostgreSQL via
`DATABASE_URL` (also available as a `postgres` profile in
`docker-compose.yml`). Tables: `security_logs`, `model_runs`, `detections`,
`alerts`. `scripts/init_database.py` is idempotent — safe to run repeatedly.
The ETL pipeline (`DataLoader.save_to_database`), `train_model.py`, and the
`/api/v1/predict` endpoint all write real rows; nothing is simulated.

## Monitoring

`GET /metrics` exposes Prometheus counters and histograms: request counts
and latency by route, records analyzed, threats detected, auth failures by
reason, rate-limit rejections, model-loaded and audit-chain-valid gauges.
Private by default (needs a `viewer` key); set `METRICS_PUBLIC=true` to
expose it unauthenticated (keep the port itself private in that case).

`AutoRetrainer.run_monitoring_cycle()` (`src/mlops/auto_retrainer.py`)
evaluates the latest model on a fresh labeled CSV, compares it against the
training-time baseline in `latest.json`, and reports both performance drift
(degradation past `retraining.drift_threshold`) and an absolute floor
(`retraining.performance_threshold`) from `config/config.yaml`. It does not
retrain automatically — it reports `needs_retraining` for the caller to act
on. `ModelRegistry` (MLflow-backed model versioning) degrades gracefully and
logs a warning if no MLflow server is reachable, instead of hanging.

## Testing and CI

```bash
pytest -q                                               # full suite
pytest -q -k "not tensorflow"                           # skip TF-dependent tests
ruff check src scripts tests --select E9,F               # lint (syntax + pyflakes)
```

70 tests, covering the database layer, audit chain (including simulated
history-rewrite and truncation attacks), API auth/CORS/validation/rate
limiting, model artifact save/load/tamper-detection, the monitoring cycle,
testnet anchoring (against an in-memory Ethereum chain), the held-out
evaluation module, and the dashboard (login, API client, page rendering,
and a direct check that no simulated numbers remain in its source). Tests
needing TensorFlow or web3 skip cleanly when those packages are absent.

`.github/workflows/ci.yml` runs the lint and test suite, validates
`docker-compose.yml`, builds the Docker image, and starts the built
container to smoke-test `/health` and a real authenticated request against
it — not just that the image builds.

## Honest evaluation results

The model shipped in `data/models/` reports **99.2% accuracy** on its
training-split test set. On NSL-KDD's official held-out `KDDTest+`
(`python scripts/evaluate_model.py`), the same model scores:

| Metric | Training split | Held-out KDDTest+ | Harder KDDTest-21 |
|---|---:|---:|---:|
| Accuracy | 99.2% | **78.3%** | **58.9%** |
| Precision | 99.2% | 93.4% | — |
| Recall | 99.0% | 66.7% | 55.9% |
| False positive rate | — | 6.2% | — |

Detection rate by attack family on the held-out set:

| Family | Detection rate |
|---|---:|
| DoS | 84.7% |
| Probe | 82.1% |
| R2L | **8.5%** |
| U2R | **10.4%** |

Attack types present in `KDDTest+` but absent from the training file
(3,752 records — `mailbomb`, `processtable`, `snmpguess`, `snmpgetattack`,
`httptunnel`, and others) are detected only **43.1%** of the time. Several
individual attack types are almost never caught:
`mailbomb` (0.0%), `processtable` (0.3%), `snmpguess` (0.3%),
`snmpgetattack` (0.6%), `httptunnel` (1.5%), `guess_passwd` (2.0%).

**Read this as**: the model is reasonably effective against DoS and
network-scanning (Probe) traffic similar to what it trained on, and
unreliable against R2L/U2R-style attacks and against attack types it has
not seen — which is the regime that matters most in practice, since a
production IDS mainly needs to catch what it has not seen before. Do not
quote the 99% figure as expected real-world performance.

## Known limitations

- **Audit log**: single node, no consensus or peers; see
  [Audit log](#audit-log) for what local verification cannot catch and what
  testnet anchoring does and does not address.
- **Rate limiting** is per-process; it multiplies across multiple API
  workers or replicas rather than being shared.
- **Model artifact integrity**: the Keras `.h5` file's SHA-256 is checked
  against the value recorded at save time, which catches accidental
  corruption or in-place edits, but a fully replaced (model file +
  regenerated hash in a self-modified `_preproc.json`) attack is not
  detected — only anchoring the audit log's record of the training event
  addresses that, and only for models trained after anchoring began.
- **Dashboard auth** is a single shared password with per-session backoff,
  suitable for a small team; for anything larger, put it behind a reverse
  proxy or SSO.
- **Model performance**: see
  [Honest evaluation results](#honest-evaluation-results) above — NSL-KDD
  itself is a benchmark dataset from 2009, and even held-out performance on
  it does not guarantee performance on real, current network traffic.
- **MLflow model registry** (`ModelRegistry` in `auto_retrainer.py`)
  requires a running MLflow server to actually register/promote/retrieve
  models; without one it logs a warning and those features are inert
  (training, prediction, and monitoring do not depend on it).

## Project layout

```
config/             config.yaml, .env.example
data/               raw/, processed/, models/, blockchain/ (git-ignored except structure)
docs/               additional documentation
scripts/            init_database.py, download_datasets.py, train_model.py,
                    evaluate_model.py, migrate_model_artifacts.py
src/
  api/              FastAPI app, Prometheus metrics
  blockchain/       hash-chained audit log, testnet anchoring
  dashboard/        Streamlit app, auth, API client
  db/               SQLAlchemy models, repository, engine/session
  etl/              extract/transform/load pipeline
  evaluation/       NSL-KDD held-out evaluation
  mlops/            model registry, monitoring, auto-retrainer
  models/           MLP-GRU threat detector
  security/         API-key auth, rate limiting
  utils/            config loader, logger
tests/              70 tests across all of the above
Dockerfile          non-root, CPU TensorFlow, healthcheck
docker-compose.yml  api, dashboard, optional postgres profile
.github/workflows/  CI: lint, test, compose validation, image build + smoke test
```
