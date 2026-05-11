# Setup and Installation Guide

## Prerequisites

### System Requirements
- Windows 10/11 or Linux
- Python 3.11+
- SQL Server 2019+
- Docker (optional, for containerization)
- Git

### Python Dependencies
```bash
pip install -r requirements.txt
pip install -r requirements_api.txt
```

---

## Installation Steps

### 1. Clone Repository
```bash
git clone <repository-url>
cd anomaly-detector
```

### 2. Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
pip install -r requirements_api.txt
```

### 4. Configure Environment
Create `.env` file with:
```env
# Database
DB_SERVER=your_server
DB_DATABASE=your_database
DB_USER=your_user
DB_PASSWORD=your_password

# MLflow
MLFLOW_TRACKING_DIR=backend/mlops/mlruns

# API
API_HOST=0.0.0.0
API_PORT=8000
```

### 5. Initialize Database
```bash
# Run database setup scripts
python setup_mlflow.py
```

### 6. Start Services

#### Backend API
```bash
python -m uvicorn api.api:app --reload --host 0.0.0.0 --port 8000
```

#### MLflow UI
```bash
mlflow ui --backend-store-uri file:backend/mlops/mlruns
```

#### Frontend (C#)
```bash
cd ConfigManagementUI
dotnet run
```

---

## Docker Setup

### Build Docker Image
```bash
docker build -f Docker/Dockerfile.windows -t anomaly-detector:latest .
```

### Run Docker Container
```bash
docker run -p 8000:8000 -p 5000:5000 anomaly-detector:latest
```

### Docker Compose
```bash
docker-compose up -d
```

---

## Configuration

### MLflow Configuration
Located in `backend/mlops/mlflow_config.py`:
- Tracking URI: `file:backend/mlops/mlruns`
- Artifact Root: `backend/mlops/mlruns/artifacts`
- Experiments: Automatically created

### Database Configuration
Located in `backend/db_service.py`:
- Connection pooling enabled
- Default pool size: 3000
- Supports SQL Server with pyodbc

### API Configuration
Located in `api/api.py`:
- Host: 0.0.0.0
- Port: 8000
- CORS enabled for frontend

---

## Model Setup

### Download Pre-trained Models
```bash
# Models are stored in backend/model/
# - autoencoder.h5
# - isolation_forest.pkl
# - autoencoder_scaler.pkl
# - isolation_forest_scaler.pkl
```

### Train New Models
```bash
# Train Isolation Forest
python backend/train_isolation_forest.py

# Train Autoencoder
python backend/train_autoencoder.py
```

### Model Versioning
```bash
# List available versions
python list_model_versions.py

# Activate specific version
python activate_model_version.py --version 1.0.0
```

---

## Testing

### Run All Tests
```bash
python test_mlflow.py
python test_general.py
```

### Run Specific Test
```bash
python -m unittest test_mlflow.TestMLflowConfig
```

### Generate Test Report
```bash
python test_mlflow.py > test_results.txt
```

---

## Verification

### Check API Health
```bash
curl http://localhost:8000/health
```

### Check MLflow
```bash
# Open browser
http://localhost:5000
```

### Check Database Connection
```bash
python -c "from backend.db_service import get_db_service; db = get_db_service(); print('Connected')"
```

---

## Troubleshooting

### Issue: Database Connection Failed
**Solution:**
1. Verify SQL Server is running
2. Check connection string in `.env`
3. Verify credentials
4. Check firewall settings

### Issue: MLflow Not Starting
**Solution:**
1. Check `backend/mlops/mlruns` directory exists
2. Verify write permissions
3. Check port 5000 is available

### Issue: API Port Already in Use
**Solution:**
```bash
# Use different port
python -m uvicorn api.api:app --port 8001
```

### Issue: Import Errors
**Solution:**
1. Verify virtual environment is activated
2. Reinstall dependencies: `pip install -r requirements.txt`
3. Check Python path

---

## Performance Tuning

### Database Connection Pool
```python
# In backend/db_service.py
pool_size = 3000  # Adjust based on load
```

### Model Inference
```python
# Use GPU if available
import tensorflow as tf
print(tf.config.list_physical_devices('GPU'))
```

### API Workers
```bash
# Use multiple workers
gunicorn -w 4 -b 0.0.0.0:8000 api.api:app
```

---

## Security

### API Authentication
- Basic Auth enabled
- Admin key required for sensitive operations
- CORS configured for frontend only

### Database Security
- Connection pooling with timeout
- Parameterized queries to prevent SQL injection
- Credentials stored in `.env` (not in code)

### Model Security
- Model versioning for audit trail
- MLflow registry for model governance
- Artifact storage with access control

---

## Monitoring

### MLflow Tracking
- All experiments tracked in MLflow
- Metrics and parameters logged
- Model artifacts stored

### Drift Monitoring
- Automatic drift detection
- Results saved in `backend/model/drift_results/`
- Alerts for significant drift

### Logging
- Application logs in console
- Database logs in SQL Server
- API logs in FastAPI

---

## Maintenance

### Regular Tasks
1. Monitor drift detection results
2. Review model performance metrics
3. Update models as needed
4. Clean up old artifacts

### Backup
```bash
# Backup MLflow data
cp -r backend/mlops/mlruns backup/

# Backup database
# Use SQL Server backup tools
```

### Updates
```bash
# Update dependencies
pip install --upgrade -r requirements.txt

# Update models
python backend/train_isolation_forest.py
```

---

## Support

For issues or questions:
1. Check logs for error messages
2. Review documentation in `docs/`
3. Check test results in `docs/MLFLOW_TEST_REPORT.md`
4. Verify all prerequisites are installed

---

**Last Updated:** May 11, 2026  
**Status:** ✅ Ready for Deployment
