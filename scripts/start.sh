#!/bin/bash
set -e

echo "=== Starting Credit Risk Intelligence Platform ==="

# 1. Validate environment variables
if [ -z "$GEMINI_API_KEY" ]; then
    echo "WARNING: GEMINI_API_KEY is not set. Talk-to-Data chatbot features may not function."
fi

# 2. Check model artifacts exist
REQUIRED_MODELS=(
    "models/preprocessor.pkl"
    "models/iso_forest.pkl"
    "models/logistic_reg.pkl"
    "models/random_forest.pkl"
    "models/xgboost_model.pkl"
    "models/meta_learner.pkl"
    "models/shap_explainer.pkl"
)

TRAIN_REQUIRED=0
echo "Verifying model artifacts..."
for model in "${REQUIRED_MODELS[@]}"; do
    if [ ! -f "$model" ]; then
        echo "Required model artifact '$model' is missing."
        TRAIN_REQUIRED=1
    fi
done

if [ $TRAIN_REQUIRED -eq 1 ]; then
    echo "One or more model artifacts are missing. Automatically starting model training pipeline..."
    python src/ml/train.py
    echo "Model training completed successfully."
else
    echo "All required model artifacts found. Skipping training."
fi

# 3. Create database if missing
if [ ! -f "sql/credit_risk.db" ]; then
    echo "Database 'sql/credit_risk.db' not found. Initializing new database..."
    python -c "from src.database.db_manager import DatabaseManager; DatabaseManager().initialize()"
    echo "Database initialized with schema."
else
    echo "Database exists."
fi

# 4. Start backend (FastAPI serves both API and static frontend)
echo "Starting FastAPI backend and frontend on port 8000..."
exec uvicorn src.api.main:app --host 0.0.0.0 --port 8000
