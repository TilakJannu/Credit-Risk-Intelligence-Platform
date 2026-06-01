# Credit Risk Intelligence Platform

AI-powered credit default prediction, explainability, business rules, and natural-language analytics built on the [Home Credit Default Risk](https://www.kaggle.com/competitions/home-credit-default-risk/data) dataset.

The platform helps credit analysts score applicants, understand model drivers with SHAP, explore portfolio data in plain English, and deploy the full workflow with Docker.

---

## Architecture Overview

```text
Home Credit CSVs
      ↓
Data Loader & Validation
      ↓
EDA + Feature Engineering (+ feature categorization)
      ↓
Preprocessing (impute, encode, scale, split)
      ↓
Isolation Forest (anomaly score feature)
      ↓
Base Models: Logistic Regression | Random Forest | XGBoost
      ↓
Stacking Meta-Learner (Logistic Regression on OOF predictions)
      ↓
Risk Scoring (PD, risk score, LOW / MEDIUM / HIGH bands)
      ↓
SHAP Explainability + Surrogate Business Rules
      ↓
SQLite Analytics DB
      ↓
Talk-to-Data (Gemini NL→SQL → query → business insight)
      ↓
FastAPI + Static Dashboard
      ↓
Docker Deployment
```

**Runtime components**

| Layer | Technology |
|-------|------------|
| API | FastAPI, Uvicorn |
| ML | scikit-learn, XGBoost, SHAP |
| Database | SQLite |
| LLM | Google Gemini (`gemini-2.5-flash`) |
| Frontend | HTML, CSS, JavaScript (Plotly.js for charts) |
| Deployment | Docker, Docker Compose |

See also `ARCHITECTURE.md` for extended design notes.

---

## Project Structure

```text
credit_risk_platform/
├── data/                    # Home Credit CSV files (Excluded from GitHub; download from Kaggle)
├── documents/               # EDA, evaluation, SHAP, rules, talk-to-data docs
├── models/                  # Serialized .pkl artifacts
├── notebooks/               # EDA notebook + eda.py runner
├── scripts/                 # Utility scripts (e.g. verify_nl_queries.py)
├── sql/schema.sql           # SQLite DDL
├── tests/                   # Unit / integration tests
├── src/
│   ├── api/main.py          # FastAPI application
│   ├── data/                # Loader, feature engineering, preprocessing
│   ├── database/            # SQLite manager + build script
│   ├── explainability/      # SHAP + business rules
│   ├── frontend/static/     # Dashboard UI
│   ├── ml/                  # Train, evaluate, predict
│   ├── talk_to_data/        # NL→SQL, insights, verified queries
│   └── utils/               # Config, logging, helpers
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

---

## Setup and Run

### 1. Download Dataset
The raw Kaggle dataset is ~2.6 GB and has been excluded from the GitHub repository (`/data/` is in `.gitignore`) to optimize repo size. To run the full data pipeline and model retraining:
1. Download the dataset from [Home Credit Default Risk on Kaggle](https://www.kaggle.com/competitions/home-credit-default-risk/data).
2. Create a `/data` directory in the project root and place the downloaded CSV files inside it.

> [!NOTE]
> Pre-trained models (`models/`), pre-computed metrics (`documents/`), and the SQLite database (`sql/credit_risk.db`) are already committed to the repository, meaning you can run the web application or docker-compose setup directly without running the data extraction and training scripts.

### 2. Local environment

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux / macOS
pip install -r requirements.txt
copy .env.example .env          # Windows
# cp .env.example .env          # Linux / macOS
```

Set `GEMINI_API_KEY` in `.env` before using the Talk-to-Data chatbot.

### 2. Build pipeline artifacts (first time)

Run in order:

```bash
python -m src.data.loader
python -m notebooks.eda
python -m src.data.feature_engineering
python -m src.data.preprocessor
python -m src.ml.train
python -m src.ml.evaluate
python -m src.database.build_database
```

Optional post-training artifacts:

```bash
python -c "from src.explainability.rule_generator import generate_business_rules; generate_business_rules()"
python -c "from src.explainability.shap_engine import ShapExplainer; ShapExplainer().save_global_outputs(__import__('pandas').read_parquet('documents/processed/x_train_scored.parquet').head(500))"
```

### 3. Start the application

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000**

Dashboard tabs: Executive Dashboard · EDA · Model Performance · Prediction · Explainability · Rules · AI Chatbot

### 4. Part 5: Dockerized Deployment (Single Command)

```bash
docker-compose up --build
```

This starts the containerized FastAPI web application and database. Pre-built `models/`, `documents/`, and `sql/credit_risk.db` are mounted automatically via volumes (defined in `docker-compose.yml`) so the application is ready to serve immediately. If needed, the data pipelines can be run inside or outside the container.

---

## Model Selection Rationale

**Problem:** Binary classification of loan default on a highly imbalanced tabular dataset (~8% positive class).

**Approach:** A stacking ensemble that combines complementary learners:

| Model | Role |
|-------|------|
| **Logistic Regression** | Interpretable linear baseline; fast; good calibrated probabilities with `class_weight="balanced"` |
| **Random Forest** | Captures non-linear interactions; robust on mixed feature types |
| **XGBoost** | Strong tabular performance; `scale_pos_weight` handles imbalance |
| **Isolation Forest** | Unsupervised anomaly score appended as a feature (contamination ≈ 8%) |
| **Meta-learner** | Logistic Regression trained on out-of-fold base probabilities |

**Why stacking?** Each base model emphasizes different patterns. The meta-learner learns how to weight their probabilities instead of relying on a single algorithm.

**Risk outputs**

- `default_probability` — stacked ensemble PD  
- `risk_score` — `round(PD × 1000)`  
- `risk_band` — LOW (&lt; 0.30), MEDIUM (0.30–0.60), HIGH (&gt; 0.60)

---

## Class Imbalance Strategy

- Stratified train / validation / test splits (`TEST_SIZE`, `VALIDATION_SIZE` in `.env`)
- `class_weight="balanced"` for Logistic Regression and Random Forest
- `scale_pos_weight = negatives / positives` for XGBoost
- **Primary metrics:** ROC-AUC (ranking) and **PR-AUC** (imbalanced data); recall tracked for catch-rate of defaulters
- Classification threshold for confusion matrix aligned with LOW-risk boundary (0.30)

---

## Evaluation Metrics and Results

**Test-set metrics** (stacked ensemble, from `documents/evaluation/evaluation_report.json`):

| Metric | Value | Interpretation |
|--------|-------|----------------|
| **ROC-AUC** | 0.7861 | Good ranking of defaulters vs non-defaulters |
| **PR-AUC** | 0.2863 | Realistic for ~8% default rate; preferred over accuracy |
| **Precision** | 0.1261 | Many false positives when thresholding at 0.30 |
| **Recall** | 0.8826 | Catches most actual defaulters |
| **F1** | 0.2206 | Balance of precision/recall at chosen threshold |

**Validation metrics (base models)**

| Model | ROC-AUC | PR-AUC |
|-------|---------|--------|
| logistic_reg | 0.7703 | 0.2453 |
| random_forest | 0.7590 | 0.2307 |
| xgboost_model | 0.7809 | 0.2691 |

**Stacking meta-learner (validation):** ROC-AUC 0.7825 · PR-AUC 0.2678

View in the UI: **Model Performance** tab, or `GET /evaluation`. Charts: ROC, PR, confusion matrix under `documents/evaluation/`.

Regenerate metrics:

```bash
python -m src.ml.evaluate
```

---

## LLM Prompts and Token Optimization

**Provider:** Google Gemini (`GEMINI_MODEL=gemini-2.5-flash`, configured in `.env`)

### 1. NL → SQL (`src/talk_to_data/prompt_templates.py`)

- Schema description with allowed tables/columns only  
- **7 few-shot examples** matching verified business questions  
- Rules: SELECT-only, no invented columns, `LIMIT 100` by default  
- Output: SQL text only (no markdown)

**Hallucination controls:** `SQLValidator` blocks destructive keywords, enforces single SELECT, runs `EXPLAIN QUERY PLAN` before execution.

### 2. SQL results → business insight (`build_insight_prompt`)

- Analyst persona; answer only from returned rows  
- Bounded input: max **25 rows**, **6,000 characters** of JSON preview  
- Instructions: lead with direct answer, optional bullets, no SQL in response

**Token optimization**

- Few-shot examples reused from verified query catalog (no dynamic schema bloat)  
- Truncated row previews for insight step  
- SQL step returns minimal output (query string only)  
- Read-only DB connection for execution

Prompt source files: `src/talk_to_data/prompt_templates.py`, `src/talk_to_data/nl_to_sql.py`, `src/talk_to_data/insight_generator.py`

---

## Rule Derivation Logic and Sample Outputs

**Method:** A shallow decision tree (max depth 4, `min_samples_leaf=200`) trained to approximate **high-risk** labels (`PD > 0.60`) on processed training features. Rules are extracted as readable IF/AND/THEN paths.

**Generate rules:**

```bash
python -c "from src.explainability.rule_generator import generate_business_rules; generate_business_rules()"
```

**Outputs:** `documents/rules/business_rules.json`, `business_rules.md`, `models/business_rule_tree.pkl`

**Sample rule:**

```text
IF EXT_SOURCE_3 <= -0.986
AND EXT_SOURCE_2 <= -0.024
AND EXT_SOURCE_1 <= 0.444
AND BUREAU_BUREAU_DEBT_TO_CREDIT_RATIO_MEAN <= -0.007
THEN High Risk
```

Customer-specific rules in the UI combine stacking predictions with SHAP top positive drivers.

---

## Talk-to-Data: Verified Queries

Seven natural-language questions are documented and tested:

- Catalog: `src/talk_to_data/verified_queries.py`  
- Documentation: `documents/talk_to_data/verified_queries.md`

**Offline test (no API key):**

```bash
python -m unittest tests.test_talk_to_data.TalkToDataOfflineTests -v
```

**Live test (requires `GEMINI_API_KEY`):**

```bash
set RUN_GEMINI_TESTS=1
python -m unittest tests.test_talk_to_data.TalkToDataLiveTests -v
```

**Manual report:**

```bash
python scripts/verify_nl_queries.py
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service health |
| GET | `/dashboard/kpis` | Live applicant count, default rate, risk distribution |
| GET | `/eda` | EDA report + feature categorization + chart URLs |
| GET | `/evaluation` | Model metrics and evaluation chart URLs |
| GET | `/assets/eda/{filename}` | EDA PNG charts |
| GET | `/assets/evaluation/{filename}` | Evaluation PNG charts |
| GET | `/assets/shap/{filename}` | SHAP summary image |
| GET | `/shap/global` | Global feature importance |
| POST | `/predict` | Score applicant JSON |
| POST | `/predict/lookup` | Score by customer ID |
| GET | `/predict/customer/{id}` | Score by ID |
| POST | `/explain` | SHAP for applicant JSON |
| GET | `/explain/customer/{id}` | SHAP by ID |
| GET | `/rules` | Global business rules |
| GET | `/rules/customer/{id}` | Customer-specific rules |
| POST | `/chat` | NL question → SQL → rows → business insight |

---

## Feature Categorization (EDA Deliverable)

Engineered features are grouped into business categories (bureau, repayment, demographics, etc.):

- Generated with feature store: `documents/eda/feature_categories.json`  
- Logic: `src/data/feature_categories.py`  
- Visible in UI: **EDA** tab → Feature Categorization table

---

## Security

- Secrets only via `.env` (see `.env.example`)  
- Talk-to-Data: validated **SELECT-only** SQL; destructive statements blocked  
- Read-only SQLite connections for analytics queries

---

## Known Limitations and Possible Improvements

| Limitation | Possible improvement |
|------------|---------------------|
| First prediction/explain loads all `.pkl` artifacts (cold start) | Singleton model cache at API startup |
| SQLite for analytics | Migrate to PostgreSQL for production concurrency |
| No authentication on API | Add API keys / OAuth for production |
| Classifier threshold 0.30 yields low precision | Tune threshold for business cost matrix |
| Applicant name lookup unsupported | Expected — Home Credit has no name field |
| LIME uses 800-row background sample | Precompute slimmer LIME background artifact |
| Model drift not monitored | Scheduled retraining + drift detection |


---

## Phase 5 — Final QA and Submission Readiness

Run automated smoke tests:

```bash
# Offline API + artifact checks (fast)
python scripts/smoke_test_platform.py

# Include prediction / SHAP endpoints (slower)
set RUN_ML_SMOKE_TESTS=1
python scripts/smoke_test_platform.py

# Include live Gemini Talk-to-Data tests
set RUN_GEMINI_TESTS=1
python scripts/smoke_test_platform.py
```

Manual checklist: `documents/SUBMISSION_CHECKLIST.md`

Unit tests:

```bash
python -m unittest tests.test_platform_smoke.ArtifactSmokeTests -v
python -m unittest tests.test_talk_to_data -v
```

## Explainability (aligned to final stacked score)

| Method | What it explains |
|--------|------------------|
| **Stacking SHAP** | Meta-learner contribution of each base model probability |
| **Feature SHAP** | XGBoost feature drivers |
| **Official SHAP waterfall** | `shap.plots.waterfall` PNG served at `/assets/explainability/waterfall_*.png` |
| **LIME** | Local explanation of the full stacking predictor |

---

## Major Design Decisions

1. **Applicant-level feature store** — All related tables aggregated to `SK_ID_CURR` for scoring and explainability.  
2. **Stacking over single model** — Balances interpretability (LR), robustness (RF), and accuracy (XGBoost).  
3. **Anomaly feature** — Isolation Forest score enriches features without replacing supervised models.  
4. **SQLite + NL analytics** — Lightweight deployment; Talk-to-Data runs on the same DB populated after training.  
5. **Two-step LLM** — Separate SQL generation and insight summarization to reduce hallucination and control tokens.  
6. **Vanilla frontend** — No React build step; FastAPI serves static assets for simple Docker eval.

---

## Environment Variables

See `.env.example` for all options. Key variables:

| Variable | Purpose |
|----------|---------|
| `GEMINI_API_KEY` | Talk-to-Data NL→SQL and business insights |
| `GEMINI_MODEL` | Default `gemini-2.5-flash` |
| `LOW_RISK_THRESHOLD` / `HIGH_RISK_THRESHOLD` | Risk band boundaries |
| `DATABASE_PATH` | SQLite file location |
| `MAX_TRAIN_ROWS` | Optional cap for faster local runs |

---


