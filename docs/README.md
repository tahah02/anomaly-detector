# Anomaly Detector - Documentation

Welcome to the Anomaly Detector system documentation. This folder contains comprehensive guides for setup, testing, and architecture.

## 📚 Documentation Files

### 1. **ARCHITECTURE.md**
Complete system architecture overview including:
- Component descriptions
- Data flow diagrams
- Model pipeline details
- Technology stack
- Deployment information

**When to read:** When you need to understand how the system works

---

### 2. **SETUP_GUIDE.md**
Step-by-step installation and configuration guide:
- Prerequisites and requirements
- Installation steps
- Docker setup
- Configuration details
- Model setup
- Testing procedures
- Troubleshooting

**When to read:** When setting up the system for the first time

---

### 3. **TEST_QUICK_START.md**
Quick reference for running tests:
- Test suite overview
- How to run tests
- Test coverage details
- Troubleshooting
- CI/CD integration examples

**When to read:** When running tests or setting up CI/CD

---

### 4. **MLFLOW_TEST_REPORT.md**
Detailed test execution report:
- Test results summary
- Coverage breakdown by test class
- Key features tested
- Recommendations
- Next steps

**When to read:** When reviewing test results or verifying system health

---

## 🚀 Quick Start

### For New Users
1. Read **SETUP_GUIDE.md** for installation
2. Read **ARCHITECTURE.md** to understand the system
3. Read **TEST_QUICK_START.md** to run tests

### For Developers
1. Read **ARCHITECTURE.md** for system design
2. Read **TEST_QUICK_START.md** for testing
3. Check **MLFLOW_TEST_REPORT.md** for test coverage

### For DevOps/Deployment
1. Read **SETUP_GUIDE.md** for deployment steps
2. Read **ARCHITECTURE.md** for infrastructure needs
3. Check **TEST_QUICK_START.md** for CI/CD integration

---

## 📋 System Overview

### What is Anomaly Detector?
A machine learning system that detects fraudulent transactions using:
- **Isolation Forest** - Statistical anomaly detection
- **Autoencoder** - Deep learning reconstruction-based detection
- **Hybrid Decision Engine** - Combines both models for better accuracy

### Key Features
✅ Real-time transaction analysis  
✅ Model versioning and registry  
✅ Drift monitoring  
✅ Configuration management  
✅ MLflow integration  
✅ REST API  
✅ Web UI for configuration  

---

## 🏗️ Architecture Highlights

### Backend
- **Python 3.11** with FastAPI
- **TensorFlow/Keras** for deep learning
- **scikit-learn** for traditional ML
- **MLflow** for experiment tracking

### Frontend
- **C# ASP.NET Core 8.0**
- Configuration management UI
- Drift monitoring dashboard
- Model version selection

### Infrastructure
- **SQL Server** for data persistence
- **Docker** for containerization
- **MLflow** for model management
- **NannyML** for drift detection

---

## 📊 Test Coverage

### MLflow Tests (43 tests)
- ✅ Configuration management
- ✅ Model versioning
- ✅ Retraining pipeline
- ✅ Drift monitoring
- ✅ Data fetching
- ✅ Integration workflows

### General Tests
- ✅ Input validation
- ✅ Feature engineering
- ✅ Model inference
- ✅ Decision making
- ✅ API models
- ✅ Data integration

---

## 🔧 Common Tasks

### Running the System
```bash
# Start backend API
python -m uvicorn api.api:app --reload

# Start MLflow UI
mlflow ui --backend-store-uri file:backend/mlops/mlruns

# Start frontend
cd ConfigManagementUI && dotnet run
```

### Running Tests
```bash
# Run all tests
python test_mlflow.py
python test_general.py

# Run specific test
python -m unittest test_mlflow.TestMLflowConfig
```

### Training Models
```bash
# Train Isolation Forest
python backend/train_isolation_forest.py

# Train Autoencoder
python backend/train_autoencoder.py
```

### Monitoring Drift
```bash
# Run drift monitoring
python -c "from backend.mlops.drift_monitor import get_drift_monitor; monitor = get_drift_monitor(); monitor.run_full_monitoring()"
```

---

## 📁 Directory Structure

```
anomaly-detector/
├── api/                          # FastAPI backend
│   ├── api.py                   # Main API endpoints
│   ├── models.py                # Request/response models
│   ├── helpers.py               # Utility functions
│   └── services.py              # Business logic
├── backend/                      # ML models and logic
│   ├── autoencoder.py           # Autoencoder model
│   ├── isolation_forest.py      # Isolation Forest model
│   ├── hybrid_decision.py       # Decision engine
│   ├── feature_engineering.py   # Feature extraction
│   ├── input_validator.py       # Input validation
│   ├── db_service.py            # Database service
│   ├── mlops/                   # MLOps pipeline
│   │   ├── mlflow_config.py     # MLflow configuration
│   │   ├── model_versioning.py  # Version management
│   │   ├── retraining_pipeline.py # Training pipeline
│   │   ├── drift_monitor.py     # Drift detection
│   │   └── data_fetcher.py      # Data fetching
│   └── model/                   # Trained models
├── ConfigManagementUI/          # C# ASP.NET frontend
├── Docker/                      # Docker configuration
├── docs/                        # Documentation (this folder)
├── requirements.txt             # Python dependencies
└── README.md                    # Main README
```

---

## 🔗 Related Files

### Configuration Files
- `.env` - Environment variables
- `requirements.txt` - Python dependencies
- `requirements_api.txt` - API dependencies
- `appsettings.json` - ASP.NET configuration

### Scripts
- `setup_mlflow.py` - MLflow initialization
- `list_model_versions.py` - List available models
- `activate_model_version.py` - Activate specific model
- `start_all.ps1` - Start all services

### Test Files
- `test_mlflow.py` - MLflow tests (43 tests)
- `test_general.py` - General tests

---

## ✅ Verification Checklist

Before deploying, verify:
- [ ] All dependencies installed
- [ ] Database connection working
- [ ] MLflow initialized
- [ ] Models trained and versioned
- [ ] All tests passing
- [ ] API responding to requests
- [ ] Frontend accessible
- [ ] Drift monitoring configured

---

## 📞 Support

### Documentation
- Check relevant `.md` file in this folder
- Review system logs for errors
- Check test results in MLFLOW_TEST_REPORT.md

### Troubleshooting
- See SETUP_GUIDE.md for common issues
- Check API logs for errors
- Verify database connection
- Review MLflow UI for experiment details

### Getting Help
1. Check documentation in `docs/` folder
2. Review test results and logs
3. Verify all prerequisites are installed
4. Check system configuration

---

## 📝 Document Versions

| Document | Last Updated | Status |
|----------|--------------|--------|
| ARCHITECTURE.md | May 11, 2026 | ✅ Current |
| SETUP_GUIDE.md | May 11, 2026 | ✅ Current |
| TEST_QUICK_START.md | May 11, 2026 | ✅ Current |
| MLFLOW_TEST_REPORT.md | May 11, 2026 | ✅ Current |
| README.md | May 11, 2026 | ✅ Current |

---

## 🎯 Next Steps

1. **New to the system?** → Start with SETUP_GUIDE.md
2. **Want to understand architecture?** → Read ARCHITECTURE.md
3. **Need to run tests?** → Check TEST_QUICK_START.md
4. **Reviewing test results?** → See MLFLOW_TEST_REPORT.md

---

**Last Updated:** May 11, 2026  
**Status:** ✅ Ready for Production  
**Version:** 1.0.0
