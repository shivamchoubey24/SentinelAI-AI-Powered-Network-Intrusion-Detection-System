# AI-Powered Network Intrusion Detection System

**Real-Time ETL Pipelines · Deep Learning Threat Detection · Automated MLOps Retraining · Blockchain-Secured Audit Logs**


## 📋 Overview

Traditional perimeter defenses — firewalls, signature-based IDS/IPS, and antivirus — struggle to keep pace with modern, evolving cyber threats. Networks generate enormous volumes of logs, traffic traces, and alerts that are impractical to monitor manually, and conventional log systems remain vulnerable to tampering, weakening forensic investigations and compliance audits.

**SentinelAI** is an integrated network intrusion detection system that combines **deep learning–based threat detection**, an **automated ETL pipeline**, **MLOps-driven continuous retraining**, and a **blockchain-secured, tamper-proof audit trail** — all surfaced through a real-time monitoring dashboard. It was built to demonstrate how AI, DevOps automation, and distributed-ledger principles can be combined into a single, cohesive security platform.

---

## 🎯 Key Features

- **🔄 Automated ETL Pipeline** — Extracts, cleans, normalizes, and engineers features from firewall logs, network traffic captures, and system event logs, with every operation logged immutably.
- **🧠 AI-Powered Threat Detection** — A hybrid **MLP-GRU** deep learning architecture combines dense feature extraction with temporal sequence modeling to classify intrusions, malware, phishing, and other anomalous network behavior.
- **⛓️ Blockchain-Secured Audit System** — A custom proof-of-work blockchain records every ETL run, prediction, and system event as an immutable block, enabling forensic auditing and integrity verification on demand.
- **⚙️ MLOps Automation** — Model versioning, performance monitoring, drift detection, and scheduled automatic retraining, tracked via MLflow.
- **📊 Real-Time Monitoring Dashboard** — A Streamlit interface with live metrics, threat analytics, CSV upload for on-demand analysis, ETL pipeline controls, model performance views, and blockchain audit exploration.
- **🔌 REST API** — A FastAPI backend exposing system functionality for integration with external tools.

---

## 🏗️ System Architecture

```
Raw Logs (Firewall / Traffic / System)
            │
            ▼
   ┌─────────────────┐        ┌──────────────────────┐
   │   ETL Pipeline   │──────▶│  Blockchain Logger    │  (immutable audit trail)
   └─────────────────┘        └──────────────────────┘
            │
            ▼
   ┌─────────────────┐
   │  MLP-GRU Model   │  (threat classification)
   └─────────────────┘
            │
            ▼
   ┌─────────────────┐        ┌──────────────────────┐
   │  MLOps Retrainer │◀──────│   Model Registry /    │
   │ (drift detection) │       │       MLflow          │
   └─────────────────┘        └──────────────────────┘
            │
            ▼
   ┌─────────────────────────────────────────────┐
   │  Streamlit Dashboard  /  FastAPI Backend      │
   │  (real-time monitoring, alerts, audit views)  │
   └─────────────────────────────────────────────┘
```

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **ETL & Processing** | Python, Pandas, NumPy |
| **Machine Learning / AI** | TensorFlow, Scikit-learn (MLP-GRU hybrid architecture) |
| **MLOps** | MLflow, DagsHub |
| **Blockchain** | Custom Proof-of-Work implementation, Web3.py |
| **Backend / API** | FastAPI, Uvicorn |
| **Dashboard** | Streamlit, Plotly |
| **Databases (optional)** | MongoDB, PostgreSQL |
| **Cloud (optional)** | AWS S3, EC2 |
| **Testing** | Pytest, pytest-cov |
| **AI Integration** | Google Gemini API |

---

## 📊 Datasets

- **CIC-IDS2017** — Canadian Institute for Cybersecurity intrusion detection dataset
- **UNSW-NB15** — Network intrusion dataset
- **Phishing Websites Dataset**
- **Synthetic / simulated data** — Sample firewall, traffic, and system logs auto-generated for demo and testing purposes

---

## 📁 Project Structure

```
sentinelai-network-security/
├── config/                     # YAML config + environment variable template
├── data/
│   ├── raw/                    # Raw security datasets (firewall, traffic, system)
│   ├── processed/              # Cleaned, transformed data
│   ├── models/                 # Trained model artifacts
│   └── blockchain/             # Blockchain audit log storage
├── docs/                       # Architecture, implementation, and quick-start docs
├── logs/                       # Application logs (auto-generated)
├── scripts/
│   ├── init_database.py        # Initializes directories / optional databases
│   └── download_datasets.py    # Generates/downloads sample datasets
├── src/
│   ├── api/                    # FastAPI backend
│   ├── blockchain/             # Proof-of-work blockchain logger
│   ├── dashboard/               # Streamlit monitoring dashboard
│   ├── etl/                    # Extract–Transform–Load pipeline
│   ├── mlops/                  # Automated retraining, drift detection, registry
│   ├── models/                 # MLP-GRU threat detection model
│   └── utils/                  # Config loading, logging utilities
├── tests/                      # Unit and integration tests
├── requirements.txt
├── setup_project.sh            # One-command environment setup
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- ~10 GB free disk space
- A Google Gemini API key (optional, for AI-assisted features)

### 1. Clone and set up the environment
```bash
git clone <repository-url>
cd sentinelai-network-security
chmod +x setup_project.sh
./setup_project.sh
```
This creates a virtual environment, installs dependencies from `requirements.txt`, and scaffolds the required data/log directories.

### 2. Configure environment variables
```bash
cp config/.env.example config/.env
# then edit config/.env and add your GEMINI_API_KEY (and any DB/cloud credentials)
```

### 3. Initialize and seed sample data
```bash
source venv/bin/activate
python scripts/init_database.py
python scripts/download_datasets.py
```

### 4. Run the pipeline components
```bash
# Process raw logs
python src/etl/pipeline.py

# Train / evaluate the threat detection model
python src/models/threat_detector.py

# Verify blockchain integrity
python src/blockchain/blockchain_logger.py
```

### 5. Launch the dashboard
```bash
streamlit run src/dashboard/app.py
```
Visit **http://localhost:8501** to access the live dashboard.

### 6. (Optional) Launch the API
```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🎮 Dashboard Walkthrough

| Page | Purpose |
|---|---|
| **Overview** | Live system status, threat counts, blocked IPs, and recent alerts |
| **Threat Detection** | Upload CSV network/firewall logs, preview data, and run on-demand threat analysis |
| **ETL Pipeline** | Trigger the ETL pipeline, watch live progress, and inspect processed files |
| **Model Performance** | Accuracy, confusion matrix, and training history for the deployed model |
| **Blockchain Audit** | Verify chain integrity, browse audit logs, export compliance reports |
| **System Settings** | Configure alert thresholds and system parameters |

---

## 🧪 Testing

```bash
pytest tests/ -v --cov=src
```

---

## 📈 Performance Targets

| Metric | Target |
|---|---|
| ETL processing (1,000 records) | < 5 seconds |
| Model accuracy | 95%+ |
| Blockchain integrity | 100% valid |
| Dashboard load time | < 3 seconds |

---

## 🗺️ Roadmap

- [ ] Production database integration (MongoDB / PostgreSQL)
- [ ] Real-time streaming ingestion via Apache Kafka
- [ ] Email / Slack alerting for high-severity threats
- [ ] User authentication and role-based access
- [ ] Containerized deployment (Docker / Kubernetes)
- [ ] Cloud deployment reference architecture (AWS/Azure/GCP)

---

## Author
Shivam Choubey
