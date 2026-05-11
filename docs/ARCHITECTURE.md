# System Architecture

## Overview
This document describes the architecture of the Anomaly Detector system.

## Components

### 1. Backend (Python)
- **API Layer** (`api/`)
  - FastAPI endpoints for transaction analysis
  - Request/response models
  - Authentication and authorization

- **ML Models** (`backend/`)
  - Isolation Forest for anomaly detection
  - Autoencoder for reconstruction-based detection
  - Hybrid decision engine combining both models

- **MLOps** (`backend/mlops/`)
  - Model versioning and registry
  - Drift monitoring
  - Retraining pipeline
  - Data fetching and feature engineering

- **Database** (`backend/db_service.py`)
  - SQL Server connection management
  - Configuration storage
  - Transaction logging

### 2. Frontend (C# ASP.NET)
- **ConfigManagementUI**
  - Configuration management interface
  - Model version selection
  - Drift monitoring dashboard
  - MLflow integration

### 3. Infrastructure
- **Docker** - Containerization
- **MLflow** - Experiment tracking and model registry
- **Database** - SQL Server for persistence

## Data Flow

```
Transaction Request
    ↓
Input Validation
    ↓
Feature Engineering
    ↓
Isolation Forest Scoring
    ↓
Autoencoder Scoring
    ↓
Hybrid Decision Engine
    ↓
Risk Assessment
    ↓
Decision (Approve/Reject)
    ↓
Response + Logging
```

## Model Pipeline

### Training Pipeline
1. Data Fetching
2. Feature Engineering
3. Model Training (IF + AE)
4. Validation
5. Versioning
6. Registry

### Inference Pipeline
1. Input Validation
2. Feature Engineering
3. Model Loading
4. Scoring
5. Decision Making
6. Response

## Key Features

- **Real-time Anomaly Detection** - Instant transaction analysis
- **Model Versioning** - Track and manage model versions
- **Drift Monitoring** - Detect data and concept drift
- **Hybrid Approach** - Combine multiple detection methods
- **Configuration Management** - Dynamic threshold and rule management
- **MLflow Integration** - Experiment tracking and model registry

## Technology Stack

- **Backend**: Python 3.11, FastAPI, TensorFlow/Keras
- **Frontend**: C# ASP.NET Core 8.0
- **Database**: SQL Server
- **ML Tools**: scikit-learn, pandas, numpy, MLflow
- **Monitoring**: NannyML for drift detection
- **Containerization**: Docker

## Deployment

- Docker containers for backend and frontend
- SQL Server for data persistence
- MLflow for model management
- Configuration UI for runtime adjustments
