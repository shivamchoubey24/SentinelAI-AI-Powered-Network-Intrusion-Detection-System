# 🎯 START HERE - Quick Setup Instructions

## Welcome to Your AI-Powered Network Security System! 🛡️

Follow these simple steps to get your project running:

---

## 📋 Prerequisites Check

Before starting, make sure you have:
- ✅ Python 3.10 or higher installed
- ✅ At least 10GB free disk space
- ✅ Internet connection (for installing packages)
- ✅ A Google Gemini API key (free to get)

---

## 🚀 Three Simple Steps to Start

### Step 1: Initial Setup (First Time Only)

Open Terminal and run:

```bash
cd /Users/omsuneri/5th-Semester-Project-
./setup_project.sh
```

This will:
- Create a Python virtual environment
- Install all required packages (~5-10 minutes)
- Set up project directories

### Step 2: Configure Your API Key

```bash
# Copy the example environment file
cp config/.env.example config/.env

# Edit the file and add your Gemini API key
nano config/.env
```

**Get your Gemini API key here**: https://makersuite.google.com/app/apikey

In the `.env` file, change this line:
```
GEMINI_API_KEY=your_gemini_api_key_here
```

Save and exit (Ctrl+X, then Y, then Enter).

### Step 3: Start the Dashboard

```bash
./start_dashboard.sh
```

That's it! Your dashboard will open automatically at http://localhost:8501

---

## 🎮 Using the System

Once the dashboard opens, you can:

1. **View Overview** - See system status and metrics
2. **Run ETL Pipeline** - Click button in sidebar to process data
3. **Train Model** - Click button in sidebar to train AI model
4. **Monitor Threats** - Navigate to different pages
5. **Check Blockchain** - Verify audit log integrity

---

## 📝 Daily Usage

After initial setup, just run:

```bash
cd /Users/omsuneri/5th-Semester-Project-
./start_dashboard.sh
```

---

## 🆘 Having Issues?

### Problem: "Permission denied"
**Solution**:
```bash
chmod +x setup_project.sh
chmod +x start_dashboard.sh
```

### Problem: "Command not found"
**Solution**: Make sure Python 3.10+ is installed:
```bash
python3 --version
```

### Problem: "Module not found"
**Solution**: Run setup again:
```bash
./setup_project.sh
```

### Problem: Dashboard won't start
**Solution**: Check if virtual environment is activated:
```bash
source venv/bin/activate
streamlit run src/dashboard/app.py
```

---

## 📚 Need More Help?

Read these documents in order:

1. **PROJECT_GUIDE.md** - Detailed step-by-step guide
2. **README.md** - Project overview
3. **docs/QUICKSTART.md** - Quick reference
4. **FINAL_SUMMARY.md** - Complete project summary

---

## ✅ Success Indicators

You'll know everything is working when:
- ✅ Dashboard opens in browser
- ✅ No error messages in terminal
- ✅ Sidebar shows "System Status: 🟢 Active"
- ✅ You can click buttons and see responses

---

## 🎯 Quick Commands Reference

```bash
# First time setup
./setup_project.sh

# Edit API key
nano config/.env

# Start dashboard
./start_dashboard.sh

# Or manually:
source venv/bin/activate
streamlit run src/dashboard/app.py

# Stop dashboard
Press Ctrl+C in terminal
```

---

## 🎓 Project Information

**Project**: AI-Powered Network Security System  
**Institution**: UIET, Panjab University, Chandigarh  
**Team**: Sourav, Shubham, Om, Tanuj, Sehwag, Yatin

---

## 🎉 Ready to Start?

1. Run `./setup_project.sh`
2. Add your API key to `config/.env`
3. Run `./start_dashboard.sh`

**That's it! You're ready to demonstrate your project! 🚀**

---

**Need help?** Check PROJECT_GUIDE.md or contact your team members.

**Good luck! 🎓✨**
