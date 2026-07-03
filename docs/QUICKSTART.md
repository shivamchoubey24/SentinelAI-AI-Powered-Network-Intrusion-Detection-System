# Quick Start Guide

This guide will help you get the AI-Powered Network Security System up and running quickly.

## Prerequisites

- macOS, Linux, or Windows with WSL
- Python 3.10 or higher
- At least 10GB of free disk space
- 8GB RAM minimum (16GB recommended)

## Installation Steps

### 1. Navigate to Project Directory

```bash
cd /Users/omsuneri/5th-Semester-Project-
```

### 2. Make Setup Script Executable

```bash
chmod +x setup_project.sh
```

### 3. Run Setup Script

```bash
./setup_project.sh
```

This will:
- Create a Python virtual environment in `venv/`
- Install all required dependencies
- Create necessary directories
- Set up configuration files

### 4. Activate Virtual Environment

```bash
source venv/bin/activate
```

You should see `(venv)` in your terminal prompt.

### 5. Configure Environment Variables

```bash
cp config/.env.example config/.env
nano config/.env  # or use your preferred editor
```

**Important**: Add your API keys:
- `GEMINI_API_KEY`: Your Google Gemini API key (required for AI features)
- Other keys are optional for basic functionality

### 6. Initialize the System

```bash
# Create directories and setup databases
python scripts/init_database.py

# Download/create sample datasets
python scripts/download_datasets.py
```

## Running the System

### Option 1: Quick Start (Dashboard Only)

Launch the Streamlit dashboard:

```bash
streamlit run src/dashboard/app.py
```

The dashboard will open in your browser at `http://localhost:8501`

### Option 2: Full System

In separate terminal windows (all with venv activated):

**Terminal 1 - ETL Pipeline:**
```bash
python src/etl/pipeline.py
```

**Terminal 2 - Train Model:**
```bash
python src/models/threat_detector.py
```

**Terminal 3 - Dashboard:**
```bash
streamlit run src/dashboard/app.py
```

**Terminal 4 - API Server (Optional):**
```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

## Testing the System

### 1. Test ETL Pipeline

```bash
python src/etl/pipeline.py
```

Expected output:
- Creates processed data in `data/processed/`
- Logs operations to `logs/`
- Records blockchain entries

### 2. Test Model Training

```bash
python src/models/threat_detector.py
```

Expected output:
- Trains MLP-GRU model
- Saves model to `data/models/`
- Displays accuracy metrics

### 3. Test Blockchain

```bash
python src/blockchain/blockchain_logger.py
```

Expected output:
- Creates blockchain entries
- Verifies integrity
- Exports audit report

### 4. Test MLOps

```bash
python src/mlops/auto_retrainer.py
```

Expected output:
- Checks retraining conditions
- Logs to MLflow (if configured)
- Updates model registry

## Using the Dashboard

Once the dashboard is running, you can:

### 1. Overview Page
- View system status
- Monitor threat metrics
- See recent alerts

### 2. Threat Detection Page
- Upload data for analysis
- View historical trends
- Access threat intelligence

### 3. ETL Pipeline Page
- Start/stop pipeline
- Monitor processing status
- View pipeline metrics

### 4. Model Performance Page
- Check model accuracy
- View training history
- Manage model versions

### 5. Blockchain Audit Page
- Verify blockchain integrity
- Browse audit logs
- Export audit reports

### 6. System Settings Page
- Configure alerts
- Update API keys
- Adjust parameters

## Common Operations

### Run ETL Pipeline

```bash
python src/etl/pipeline.py
```

### Train Model

```bash
python src/models/threat_detector.py
```

### Check Blockchain Integrity

```bash
python -c "from src.blockchain.blockchain_logger import BlockchainLogger; bl = BlockchainLogger(); print('Valid' if bl.verify_integrity() else 'Invalid')"
```

### View Logs

```bash
tail -f logs/application_*.log
```

### Clear Data (Reset)

```bash
rm -rf data/processed/*
rm -rf data/models/*
rm -rf data/blockchain/*
rm -rf logs/*
```

## Troubleshooting

### Issue: ModuleNotFoundError

**Solution**: Make sure virtual environment is activated
```bash
source venv/bin/activate
```

### Issue: Permission Denied

**Solution**: Make scripts executable
```bash
chmod +x setup_project.sh
chmod +x scripts/*.py
```

### Issue: Port Already in Use

**Solution**: Use different port
```bash
streamlit run src/dashboard/app.py --server.port 8502
```

### Issue: Out of Memory

**Solution**: Reduce batch size in `config/config.yaml`
```yaml
model:
  batch_size: 128  # Reduce from 256
```

### Issue: TensorFlow GPU Not Found

**Solution**: Install TensorFlow with GPU support (optional)
```bash
pip install tensorflow[and-cuda]
```

## Getting Help

### Check Logs

```bash
tail -f logs/application_*.log
```

### Run Tests

```bash
pytest tests/ -v
```

### Verify Installation

```bash
python -c "import tensorflow; import streamlit; import mlflow; print('All packages installed successfully')"
```

## Next Steps

1. **Read Documentation**: Check `docs/` folder for detailed guides
2. **Customize Configuration**: Edit `config/config.yaml`
3. **Add Real Data**: Replace sample data with actual security logs
4. **Set Up Databases**: Configure MongoDB and PostgreSQL
5. **Deploy to Cloud**: Use Docker for deployment

## Quick Command Reference

```bash
# Activate environment
source venv/bin/activate

# Deactivate environment
deactivate

# Run dashboard
streamlit run src/dashboard/app.py

# Run ETL
python src/etl/pipeline.py

# Train model
python src/models/threat_detector.py

# Run tests
pytest tests/ -v

# View logs
tail -f logs/application_*.log

# Update dependencies
pip install -r requirements.txt --upgrade
```

## System Requirements

### Minimum
- CPU: 4 cores
- RAM: 8GB
- Storage: 10GB
- Python: 3.10+

### Recommended
- CPU: 8 cores
- RAM: 16GB
- Storage: 50GB
- Python: 3.10+
- GPU: NVIDIA with CUDA support

## Support

For issues or questions:
1. Check documentation in `docs/` folder
2. Review logs in `logs/` folder
3. Contact project team

---

**Ready to start?** Run `./setup_project.sh` and follow the steps above!
