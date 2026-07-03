# 🚀 PROJECT SETUP AND EXECUTION GUIDE

## 📋 Complete Step-by-Step Instructions

This guide will walk you through setting up and running the AI-Powered Network Security System from scratch.

---

## ✅ STEP 1: Initial Setup

### 1.1 Open Terminal
Open your terminal application on macOS.

### 1.2 Navigate to Project Directory
```bash
cd /Users/omsuneri/5th-Semester-Project-
```

### 1.3 Make Setup Script Executable
```bash
chmod +x setup_project.sh
```

### 1.4 Run Setup Script
```bash
./setup_project.sh
```

**What this does**:
- Creates Python virtual environment (`venv/`)
- Installs all dependencies
- Creates necessary directories
- Sets up configuration files

**Expected output**: You should see messages about creating venv, installing packages, and success confirmation.

---

## ✅ STEP 2: Activate Virtual Environment

### Every time you work on the project, run:

```bash
source venv/bin/activate
```

**You'll know it worked when**: Your terminal prompt shows `(venv)` at the beginning.

**To deactivate later**: Run `deactivate`

---

## ✅ STEP 3: Configure API Keys

### 3.1 Create Environment File
```bash
cp config/.env.example config/.env
```

### 3.2 Edit the File
```bash
nano config/.env
```

Or use your preferred text editor (VS Code, TextEdit, etc.)

### 3.3 Add Your Gemini API Key

Find this line:
```
GEMINI_API_KEY=your_gemini_api_key_here
```

Replace `your_gemini_api_key_here` with your actual Google Gemini API key.

**How to get Gemini API Key**:
1. Visit: https://makersuite.google.com/app/apikey
2. Sign in with Google account
3. Click "Create API Key"
4. Copy the key and paste it in `.env` file

### 3.4 Save and Exit
- In nano: Press `Ctrl+X`, then `Y`, then `Enter`
- In other editors: Save the file normally

---

## ✅ STEP 4: Initialize the System

### 4.1 Initialize Directories and Databases
```bash
python scripts/init_database.py
```

**Expected output**: Messages about creating directories and optional database setup.

### 4.2 Create Sample Data
```bash
python scripts/download_datasets.py
```

**Expected output**: Creates sample data files in `data/raw/` directories.

**What this creates**:
- `data/raw/firewall/firewall_logs.csv` - Sample firewall logs
- `data/raw/traffic/network_traffic.csv` - Sample network traffic
- `data/raw/system/system_logs.json` - Sample system logs

---

## ✅ STEP 5: Test Each Component

### 5.1 Test ETL Pipeline
```bash
python src/etl/pipeline.py
```

**Expected output**:
- "Starting ETL pipeline..."
- "Extracted X records"
- "ETL pipeline completed successfully"

**Check**: Look in `data/processed/` for new CSV file.

### 5.2 Test Blockchain
```bash
python src/blockchain/blockchain_logger.py
```

**Expected output**:
- "Testing Blockchain Security Module..."
- "Blockchain valid: True"
- "Blockchain testing completed"

**Check**: Look in `data/blockchain/` for blockchain data files.

### 5.3 Test Model Training (Optional - Takes Time)
```bash
python src/models/threat_detector.py
```

**Note**: This will take 5-10 minutes to run.

**Expected output**:
- "Starting threat detection model training..."
- Training progress with epochs
- "Model training completed successfully"

**Check**: Look in `data/models/` for model files.

---

## ✅ STEP 6: Launch the Dashboard

### 6.1 Start Streamlit Dashboard
```bash
streamlit run src/dashboard/app.py
```

**Expected output**:
```
You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501
```

### 6.2 Open in Browser
The dashboard should automatically open in your default browser. If not, visit:
```
http://localhost:8501
```

---

## 🎮 USING THE DASHBOARD

### Main Features

1. **Overview Page** (Default)
   - System status
   - Threat metrics
   - Recent alerts

2. **Threat Detection Page**
   - Upload data for analysis
   - View historical trends
   - Threat intelligence feed

3. **ETL Pipeline Page**
   - Run pipeline with one click
   - Monitor processing status
   - View pipeline metrics

4. **Model Performance Page**
   - View accuracy metrics
   - Training history
   - Model versions

5. **Blockchain Audit Page**
   - Verify integrity
   - Browse audit logs
   - Export reports

6. **System Settings Page**
   - Configure alerts
   - Update API keys
   - Adjust parameters

### Quick Actions (Sidebar)

- **🔄 Run ETL Pipeline**: Process new data
- **🤖 Retrain Model**: Update AI model
- **🔍 Verify Blockchain**: Check audit log integrity

---

## 📊 TYPICAL WORKFLOW

### For Regular Use:

1. **Start Your Session**
   ```bash
   cd /Users/omsuneri/5th-Semester-Project-
   source venv/bin/activate
   ```

2. **Launch Dashboard**
   ```bash
   streamlit run src/dashboard/app.py
   ```

3. **Use Dashboard to**:
   - Monitor threats
   - Run ETL pipeline
   - Check system health
   - View analytics

4. **When Done**:
   - Close browser
   - Press `Ctrl+C` in terminal to stop dashboard
   - Run `deactivate` to exit virtual environment

### For Development/Testing:

1. **Process New Data**:
   ```bash
   python src/etl/pipeline.py
   ```

2. **Train/Retrain Model**:
   ```bash
   python src/models/threat_detector.py
   ```

3. **Check Logs**:
   ```bash
   tail -f logs/application_*.log
   ```

4. **Run Tests**:
   ```bash
   pytest tests/ -v
   ```

---

## 🔧 TROUBLESHOOTING

### Problem: "Command not found" errors

**Solution**: Make sure virtual environment is activated
```bash
source venv/bin/activate
```

### Problem: "Module not found" errors

**Solution**: Reinstall dependencies
```bash
pip install -r requirements.txt
```

### Problem: Port 8501 already in use

**Solution**: Use a different port
```bash
streamlit run src/dashboard/app.py --server.port 8502
```

### Problem: Permission denied for scripts

**Solution**: Make scripts executable
```bash
chmod +x setup_project.sh
chmod +x scripts/*.py
```

### Problem: Out of memory during training

**Solution**: Edit `config/config.yaml` and reduce batch size
```yaml
model:
  batch_size: 128  # Reduced from 256
```

### Problem: Slow performance

**Solution**:
1. Close other applications
2. Reduce dataset size
3. Use smaller model (edit config.yaml)

---

## 📁 DIRECTORY STRUCTURE EXPLAINED

```
5th-Semester-Project-/
├── config/              # Configuration files
│   ├── .env            # Your API keys (keep secret!)
│   └── config.yaml     # System settings
│
├── data/               # All data files
│   ├── raw/           # Original data
│   ├── processed/     # Cleaned data
│   ├── models/        # Trained AI models
│   └── blockchain/    # Audit logs
│
├── logs/              # System logs (for debugging)
│
├── src/               # Source code
│   ├── dashboard/     # Streamlit dashboard
│   ├── etl/          # Data processing
│   ├── models/       # AI models
│   ├── blockchain/   # Security logging
│   ├── mlops/        # Model automation
│   └── utils/        # Helper functions
│
├── scripts/           # Utility scripts
├── tests/            # Test files
├── docs/             # Documentation
├── requirements.txt  # Python packages
└── README.md        # Project overview
```

---

## 🎯 WHAT TO DO NEXT

### For Project Demonstration:

1. ✅ **Ensure everything is working**:
   ```bash
   python src/etl/pipeline.py
   python src/blockchain/blockchain_logger.py
   streamlit run src/dashboard/app.py
   ```

2. ✅ **Prepare presentation materials**:
   - Screenshots of dashboard
   - System architecture diagram
   - Performance metrics

3. ✅ **Practice the demo**:
   - Show data processing
   - Demonstrate threat detection
   - Verify blockchain integrity
   - Explain AI model

### For Further Development:

1. 📚 **Read Documentation**:
   - `docs/architecture.md` - System design
   - `docs/implementation.md` - Technical details
   - `docs/QUICKSTART.md` - Quick reference

2. 🧪 **Add Your Own Data**:
   - Replace sample data in `data/raw/`
   - Run ETL pipeline
   - Retrain model

3. 🔧 **Customize**:
   - Edit `config/config.yaml` for settings
   - Modify dashboard in `src/dashboard/app.py`
   - Adjust model in `src/models/threat_detector.py`

---

## 📞 GETTING HELP

### Check Logs
```bash
tail -f logs/application_*.log
```

### Run Diagnostic
```bash
python -c "import tensorflow; import streamlit; import mlflow; print('All OK')"
```

### Verify Installation
```bash
which python  # Should show path in venv/
pip list      # Shows installed packages
```

---

## 🎓 PROJECT INFORMATION

**Project**: AI-Powered Network Security System  
**Institution**: UIET, Panjab University, Chandigarh  
**Course**: B.E. Information Technology (Final Year)  
**Academic Year**: 2024-2025

**Team Members**:
- Sourav Biswas (UE238103)
- Shubham Choubey (UE238101)
- Om Suneri (UE238066)
- Tanuj Ramchandani (UE238108)
- Sehwag Meena (UE238095)
- Yatin Kumar (UE238112)

**Supervisors**:
- Dr. Amandeep Verma Ma'am
- Amrit Sandhu Ma'am

---

## ✨ QUICK COMMAND REFERENCE

```bash
# Setup
./setup_project.sh                    # Initial setup
source venv/bin/activate              # Activate environment

# Initialize
python scripts/init_database.py       # Setup directories
python scripts/download_datasets.py   # Create sample data

# Run Components
python src/etl/pipeline.py           # Process data
python src/models/threat_detector.py # Train model
python src/blockchain/blockchain_logger.py  # Test blockchain
streamlit run src/dashboard/app.py   # Launch dashboard

# Testing
pytest tests/ -v                     # Run tests
tail -f logs/application_*.log       # View logs

# Maintenance
pip install -r requirements.txt --upgrade  # Update packages
deactivate                           # Exit virtual environment
```

---

## 🎉 SUCCESS INDICATORS

You'll know the system is working correctly when:

✅ Virtual environment activates without errors  
✅ ETL pipeline processes data successfully  
✅ Blockchain integrity verification passes  
✅ Dashboard opens in browser  
✅ No error messages in logs  
✅ Sample data appears in dashboard  

---

**Ready to start?** Begin with STEP 1 and work your way through! 🚀

For any issues, check the troubleshooting section or review the logs.

**Good luck with your project! 🎓**
