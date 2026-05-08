# 📚 Code Documentation - Fraud Detection System

Complete guide explaining what each file does, how it works, and why it's used.

---

## 📁 Project Structure Overview

```
anomaly-detector/
├── api/                          # FastAPI REST API
├── backend/                      # Core ML & Business Logic
├── ConfigManagementUI/           # ASP.NET Config Dashboard
├── Docker/                       # Containerization
├── data/                         # Training datasets
└── Root files                    # Scripts & configs
```

---

## 🔷 API Layer (`api/`)

### **`api/api.py`**
**What:** Main FastAPI application - REST API endpoints  
**How:** Receives HTTP requests, processes transactions, returns fraud decisions  
**Why:** External systems (mobile apps, web) need HTTP interface to check transactions

**Key Functions:**
- `POST /api/analyze-transaction` - Main fraud detection endpoint
- `GET /api/health` - System health check
- `POST /api/transaction/approve` - Manual approval
- `POST /api/transaction/reject` - Manual rejection
- `GET /api/features` - Feature management
- `POST /api/mlops/trigger-retraining` - Trigger model retraining

**Flow:**
```
Request → Validate → Get user stats → Run models → Calculate risk → Return decision
```

---

### **`api/models.py`**
**What:** Pydantic data models for request/response validation  
**How:** Defines structure and validation rules for API data  
**Why:** Ensures data integrity, auto-generates API documentation

**Key Models:**
- `TransactionRequest` - Input transaction data
- `TransactionResponse` - Fraud detection result
- `ApprovalRequest` - Manual approval data
- `RejectionRequest` - Manual rejection data

**Example:**
```python
TransactionRequest:
  - customer_id (required)
  - amount (required, must be > 0)
  - transfer_type (required, pattern: S|I|L|Q|O|M|F)
```

---

### **`api/services.py`**
**What:** Business logic services for API  
**How:** Handles pending transactions, notifications, etc.  
**Why:** Separates business logic from API routes

**Key Functions:**
- `get_pending_transactions()` - Fetch transactions awaiting approval
- `send_notification()` - Alert system for suspicious transactions

---

### **`api/helpers.py`**
**What:** Utility functions for API operations  
**How:** Authentication, validation, idempotency checks  
**Why:** Reusable helper functions to keep code DRY

**Key Functions:**
- `verify_basic_auth()` - HTTP Basic Authentication
- `verify_admin_key()` - Admin operation authorization
- `generate_idempotence_key()` - Prevent duplicate processing
- `check_idempotence()` - Check if request already processed
- `validate_transfer_request()` - Business rule validation
- `save_transaction_to_file()` - Transaction logging

---

## 🔷 Backend Layer (`backend/`)

### **`backend/hybrid_decision.py`**
**What:** Core decision engine - combines all models  
**How:** Runs Rule Engine + Isolation Forest + Autoencoder, calculates final risk  
**Why:** Multi-model approach improves accuracy and reduces false positives

**Decision Flow:**
```
1. Rule Engine Check (amount limits, velocity, beneficiary)
2. Isolation Forest ML Model (anomaly detection)
3. Autoencoder Deep Learning (pattern analysis)
4. Calculate Risk Score (weighted combination)
5. Determine Risk Level (SAFE/LOW/MEDIUM/HIGH)
6. Calculate Confidence (model agreement)
7. Return Final Decision
```

**Risk Calculation:**
```python
Base Risk (from rules) 
  + ML Boost (if ML detects anomaly)
  + AE Boost (if AE detects anomaly)
  = Final Risk Score (0.0 - 1.0)
```

---

### **`backend/rule_engine.py`**
**What:** Business rule validation engine  
**How:** Checks transaction against configurable thresholds  
**Why:** Fast, explainable rules for common fraud patterns

**Rules Checked:**
- Amount limits (per transfer type)
- Velocity checks (transactions per time window)
- Monthly spending limits
- New beneficiary detection
- Customer-specific configurations

**Example:**
```python
If amount > (user_avg + 3 × user_std):
  → Flag as suspicious
```

---

### **`backend/autoencoder.py`**
**What:** Deep learning autoencoder for anomaly detection  
**How:** Neural network learns normal patterns, flags unusual ones  
**Why:** Detects subtle fraud patterns that rules/ML miss

**Components:**
- `TransactionAutoencoder` - Neural network model class
- `AutoencoderInference` - Runtime prediction with database threshold loading

**How It Works:**
```
1. Load model & scaler
2. Load threshold from database (with 60s cache)
3. Transform transaction features
4. Calculate reconstruction error
5. Compare error vs threshold
6. Return anomaly flag + score
```

**Key Feature (Phase 2):**
- Database-first threshold loading
- JSON fallback if database fails
- 60-second smart caching
- Real-time threshold updates

---

### **`backend/train_autoencoder.py`**
**What:** Training script for autoencoder model  
**How:** Loads historical data, trains neural network, calculates threshold  
**Why:** Model needs periodic retraining on new data

**Training Process:**
```
1. Load feature_datasetv2.csv
2. Fit StandardScaler on features
3. Train autoencoder (encoder-decoder architecture)
4. Calculate reconstruction errors
5. Compute threshold: Mean + (K × StdDev)
6. Save model, scaler, threshold
```

**K-Factor Usage:**
```python
threshold = mean_error + (k_factor × std_error)
# k=3.0 is standard (99.7% of normal data)
```

---

### **`backend/isolation_forest.py`**
**What:** Isolation Forest ML model for anomaly detection  
**How:** Scikit-learn ensemble method isolates outliers  
**Why:** Fast, effective for high-dimensional anomaly detection

**How It Works:**
```
1. Build random decision trees
2. Anomalies are isolated faster (fewer splits)
3. Calculate anomaly score (-1 to 1)
4. Normalize to 0-1 range
5. Compare against threshold
```

---

### **`backend/train_isolation_forest.py`**
**What:** Training script for Isolation Forest  
**How:** Loads data, trains model, saves to pickle  
**Why:** Model needs training on historical transaction patterns

---

### **`backend/feature_engineering.py`**
**What:** Feature calculation and transformation  
**How:** Converts raw transaction data into ML features  
**Why:** ML models need engineered features, not raw data

**Features Created:**
- Amount ratios (vs user average, max)
- Velocity metrics (transactions per time window)
- Deviation scores (z-scores)
- Time-based features (hour, day, weekend)
- Behavioral features (new beneficiary, international ratio)

---

### **`backend/db_service.py`**
**What:** Database connection and query service  
**How:** Connection pooling, parameterized queries, error handling  
**Why:** Centralized, secure database access

**Key Functions:**
- `connect()` / `disconnect()` - Connection management
- `execute_query()` - SELECT queries (returns DataFrame)
- `execute_non_query()` - INSERT/UPDATE/DELETE
- `get_all_user_stats()` - User transaction history
- `check_new_beneficiary()` - First-time recipient check
- `get_velocity_metrics()` - Transaction frequency
- `get_customer_checks_config()` - Customer-specific rules
- `get_thresholds()` - Load all thresholds from database

**Connection Pooling:**
```python
Pool size: 3000 connections
Reuses connections for performance
Thread-safe for concurrent requests
```

---

### **`backend/utils.py`**
**What:** Shared utility functions  
**How:** Model loading, feature lists, common operations  
**Why:** Avoid code duplication across modules

**Key Functions:**
- `load_model()` - Load Isolation Forest model
- `get_dynamic_model_features()` - Get feature list
- `MODEL_FEATURES` - Standard feature set (43 features)

---

### **`backend/velocity_service.py`**
**What:** Real-time velocity calculation  
**How:** Counts transactions in time windows (30s, 10min, 1hr)  
**Why:** Detect rapid-fire fraud attempts

**Metrics:**
```
- txn_count_30s: Transactions in last 30 seconds
- txn_count_10min: Transactions in last 10 minutes
- txn_count_1hour: Transactions in last hour
- time_since_last_txn: Seconds since last transaction
```

---

### **`backend/input_validator.py`**
**What:** Input data validation and sanitization  
**How:** Checks data types, ranges, formats  
**Why:** Prevent invalid data from breaking models

---

## 🔷 MLOps Layer (`backend/mlops/`)

### **`backend/mlops/model_versioning.py`**
**What:** Model version management system  
**How:** Tracks model versions, metadata, activation  
**Why:** Safely deploy new models, rollback if needed

**Features:**
- Version tracking (v1.0.0, v1.1.0, etc.)
- Metadata storage (training date, metrics, features)
- Active version management
- Rollback capability

**Version Structure:**
```
backend/model/versions/
├── v1.0.0/
│   ├── isolation_forest.pkl
│   ├── autoencoder.h5
│   └── metadata.json
└── v1.1.0/
    ├── isolation_forest.pkl
    ├── autoencoder.h5
    └── metadata.json
```

---

### **`backend/mlops/retraining_pipeline.py`**
**What:** Automated model retraining workflow  
**How:** Fetches new data, trains models, validates, deploys  
**Why:** Models degrade over time, need periodic updates

**Pipeline Steps:**
```
1. Fetch new transaction data
2. Validate data quality
3. Train Isolation Forest
4. Train Autoencoder
5. Validate new models
6. Compare with current models
7. Create new version
8. Update database thresholds
9. Log results
```

---

### **`backend/mlops/drift_monitor.py`**
**What:** Model drift detection system  
**How:** Compares current data distribution vs training data  
**Why:** Detect when model performance degrades

**Checks:**
- Feature distribution changes
- Prediction distribution changes
- Performance metric degradation
- Statistical tests (KS test, Chi-square)

**Triggers Retraining When:**
- Drift score > threshold
- Performance drops significantly
- Data distribution shifts

---

### **`backend/mlops/scheduler.py`**
**What:** Background job scheduler  
**How:** APScheduler runs periodic tasks  
**Why:** Automate drift monitoring and retraining

**Scheduled Jobs:**
- Drift monitoring: Every 6 hours
- Model retraining: Weekly (if drift detected)
- Cleanup old logs: Daily

---

### **`backend/mlops/data_fetcher.py`**
**What:** Fetch training data from database  
**How:** Queries recent transactions, applies filters  
**Why:** Retraining needs fresh data

**Data Selection:**
```
- Last 90 days of transactions
- Approved + rejected transactions
- Minimum 10,000 samples
- Balanced fraud/non-fraud ratio
```

---

## 🔷 Config Management UI (`ConfigManagementUI/`)

### **`ConfigManagementUI/Controllers/ConfigController.cs`**
**What:** ASP.NET MVC controller for configuration management  
**How:** CRUD operations on database config tables  
**Why:** Non-technical users need UI to adjust thresholds

**Endpoints:**
- `GET /Config/Thresholds` - View all thresholds
- `POST /Config/UpdateThreshold` - Update threshold value
- `GET /Config/Features` - View feature flags
- `POST /Config/ToggleFeature` - Enable/disable features
- `GET /Config/CustomerConfig` - Customer-specific rules

**Key Feature (Phase 1):**
- Added `IsActive` toggle for thresholds
- Real-time threshold updates (no restart needed)

---

### **`ConfigManagementUI/Controllers/DriftController.cs`**
**What:** Drift monitoring dashboard controller  
**How:** Displays drift detection results, charts  
**Why:** Visualize model health and data changes

**Views:**
- Drift history
- Feature distribution changes
- Model performance metrics
- Retraining recommendations

---

### **`ConfigManagementUI/Models/DbModels/`**
**What:** Entity Framework database models  
**How:** C# classes map to SQL tables  
**Why:** Type-safe database access in .NET

**Key Models:**
- `ThresholdConfig` - System thresholds
- `CustomerAccountTransferTypeConfig` - Customer rules
- `FeaturesConfig` - Feature flags
- `ModelVersionConfig` - Model versions
- `DriftMonitoringResult` - Drift detection results
- `RetrainingConfig` - Retraining settings

---

### **`ConfigManagementUI/Views/Config/Thresholds.cshtml`**
**What:** Razor view for threshold management  
**How:** HTML + C# for dynamic UI  
**Why:** User-friendly interface for threshold editing

**Features (Phase 1):**
- Table view of all thresholds
- Inline editing
- IsActive toggle switch
- Save/Cancel buttons
- Validation

---

## 🔷 Root Level Files

### **`list_model_versions.py`**
**What:** CLI script to list all model versions  
**How:** Queries model_versioning system, outputs JSON  
**Why:** Quick way to see available versions

**Usage:**
```bash
python list_model_versions.py
```

**Output:**
```json
{
  "current_version": "v1.1.0",
  "total_versions": 3,
  "versions": [
    {"version": "base", "is_active": false},
    {"version": "v1.0.0", "is_active": false},
    {"version": "v1.1.0", "is_active": true}
  ]
}
```

---

### **`activate_model_version.py`**
**What:** CLI script to activate a model version  
**How:** Updates current_version.txt, copies model files  
**Why:** Safe model deployment and rollback

**Usage:**
```bash
python activate_model_version.py v1.1.0
```

**Process:**
```
1. Validate version exists
2. Check model files present
3. Update current_version.txt
4. Copy models to active directory
5. Restart API (if needed)
```

---

### **`start_all.ps1`**
**What:** PowerShell script to start all services  
**How:** Launches API, Config UI, and dependencies  
**Why:** One-command startup for development

**Starts:**
```powershell
1. Python API (port 8000)
2. Config UI (port 5202)
3. Background scheduler
```

---

### **`.env`**
**What:** Environment configuration file  
**How:** Key-value pairs for sensitive config  
**Why:** Keep secrets out of code, easy deployment

**Contains:**
- Database credentials
- API keys
- Port numbers
- Feature flags

**Security:** Never commit to git (in .gitignore)

---

### **`requirements.txt`**
**What:** Python package dependencies  
**How:** pip install -r requirements.txt  
**Why:** Reproducible environment

**Key Packages:**
- fastapi - Web framework
- tensorflow - Deep learning
- scikit-learn - ML algorithms
- pandas - Data manipulation
- pyodbc - Database connection

---

### **`requirements_api.txt`**
**What:** Minimal dependencies for API only  
**How:** Subset of requirements.txt  
**Why:** Smaller Docker images for production

---

### **`postman_collection.json`**
**What:** Postman API test collection  
**How:** Import into Postman for testing  
**Why:** Easy API testing and documentation

**Includes:**
- All API endpoints
- Sample requests
- Authentication
- Test assertions

---

### **`README.md`**
**What:** Project documentation  
**How:** Markdown formatted guide  
**Why:** Onboarding, setup instructions, architecture overview

---

### **`AUTOENCODER_PARAMETERS_EXPLAINED.md`**
**What:** Detailed guide for autoencoder parameters  
**How:** Explains K-factor, threshold, score boost  
**Why:** Help users tune detection sensitivity

---

## 🔷 Docker Files

### **`Docker/Dockerfile.windows`**
**What:** Docker image definition for Windows  
**How:** Multi-stage build for API + Config UI  
**Why:** Containerized deployment

**Stages:**
```dockerfile
1. Base: Python + .NET runtime
2. API: Install Python dependencies
3. Config UI: Build .NET application
4. Final: Combine both services
```

---

### **`.dockerignore`**
**What:** Files to exclude from Docker build  
**How:** Pattern matching like .gitignore  
**Why:** Smaller images, faster builds

**Excludes:**
- .git/
- __pycache__/
- *.pyc
- node_modules/
- bin/, obj/

---

## 🔷 Data Files

### **`data/feature_datasetv2.csv`**
**What:** Training dataset with engineered features  
**How:** Historical transactions with 43+ features  
**Why:** Train ML models on real patterns

**Columns:**
- Transaction features (amount, type, time)
- User features (avg, std, frequency)
- Velocity features (counts, ratios)
- Behavioral features (new beneficiary, international)
- Label (fraud/not fraud)

---

## 🎯 Key Workflows

### **Transaction Processing Flow:**
```
1. API receives transaction (api.py)
2. Validate input (models.py, helpers.py)
3. Check idempotency (helpers.py)
4. Fetch user stats (db_service.py)
5. Check new beneficiary (db_service.py)
6. Get velocity metrics (velocity_service.py)
7. Run hybrid decision (hybrid_decision.py)
   ├─ Rule engine (rule_engine.py)
   ├─ Isolation Forest (isolation_forest.py)
   └─ Autoencoder (autoencoder.py)
8. Calculate risk score
9. Determine decision
10. Save transaction (helpers.py)
11. Return response
```

---

### **Model Retraining Flow:**
```
1. Scheduler triggers (scheduler.py)
2. Check drift (drift_monitor.py)
3. If drift detected:
   ├─ Fetch new data (data_fetcher.py)
   ├─ Train Isolation Forest (train_isolation_forest.py)
   ├─ Train Autoencoder (train_autoencoder.py)
   ├─ Validate models (retraining_pipeline.py)
   ├─ Create new version (model_versioning.py)
   └─ Update database thresholds (db_service.py)
4. Log results
5. Notify admins
```

---

### **Configuration Update Flow:**
```
1. User opens Config UI (http://localhost:5202)
2. Navigate to Thresholds page (Thresholds.cshtml)
3. Edit threshold value
4. Click Save (ConfigController.cs)
5. Update database (ThresholdConfig table)
6. API loads new value within 60s (autoencoder.py cache)
7. New transactions use updated threshold
```

---

## 🔐 Security Features

### **Authentication:**
- HTTP Basic Auth for API (helpers.py)
- Admin key for sensitive operations
- Database connection encryption

### **Input Validation:**
- Pydantic models (models.py)
- SQL parameterized queries (db_service.py)
- Input sanitization (input_validator.py)

### **Data Protection:**
- Environment variables for secrets (.env)
- TLS for database connections
- Audit logging for all changes

---

## 📊 Monitoring & Observability

### **Logging:**
- Python logging module (all files)
- Transaction logs (helpers.py)
- Error tracking
- Performance metrics

### **Health Checks:**
- `/api/health` endpoint
- Database connectivity
- Model availability
- System resources

### **Metrics:**
- Transaction volume
- Fraud detection rate
- False positive rate
- Model performance
- API response time

---

## 🚀 Deployment Checklist

### **Prerequisites:**
- [ ] Python 3.11+
- [ ] .NET 8.0 SDK
- [ ] SQL Server accessible
- [ ] Redis (optional, for caching)

### **Configuration:**
- [ ] Update .env with production values
- [ ] Update appsettings.json with DB connection
- [ ] Set API_USERNAME and API_PASSWORD
- [ ] Configure ADMIN_KEY

### **Database:**
- [ ] Run schema migrations
- [ ] Populate ThresholdConfig table
- [ ] Create indexes for performance

### **Models:**
- [ ] Train initial models
- [ ] Validate model performance
- [ ] Set baseline thresholds

### **Testing:**
- [ ] Run unit tests
- [ ] Test API endpoints (Postman)
- [ ] Verify Config UI access
- [ ] Test end-to-end flow

### **Production:**
- [ ] Build Docker images
- [ ] Deploy containers
- [ ] Configure load balancer
- [ ] Set up monitoring
- [ ] Enable alerting

---

## 📞 Support & Maintenance

### **Common Issues:**

**Issue:** API returns 500 error  
**Check:** Database connection, model files exist, logs

**Issue:** Config UI not loading  
**Check:** Port 5202 available, database accessible, .NET runtime

**Issue:** High false positive rate  
**Fix:** Increase autoencoder_threshold in Config UI

**Issue:** Missing fraud detection  
**Fix:** Decrease threshold, increase AE_SCORE_BOOST

### **Maintenance Tasks:**

**Daily:**
- Monitor error logs
- Check API health
- Review flagged transactions

**Weekly:**
- Review drift metrics
- Adjust thresholds if needed
- Check model performance

**Monthly:**
- Retrain models
- Update documentation
- Review security logs

