CREATE TABLE IF NOT EXISTS customers (
    sk_id_curr INTEGER PRIMARY KEY,
    target INTEGER,
    income_total REAL,
    credit_amount REAL,
    annuity REAL,
    gender TEXT,
    education_type TEXT,
    family_status TEXT,
    occupation_type TEXT,
    housing_type TEXT,
    age_years REAL,
    employment_years REAL
);

CREATE TABLE IF NOT EXISTS predictions (
    prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sk_id_curr INTEGER,
    default_probability REAL NOT NULL,
    risk_score INTEGER NOT NULL,
    risk_band TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sk_id_curr) REFERENCES customers (sk_id_curr)
);

CREATE TABLE IF NOT EXISTS shap_outputs (
    shap_id INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_id INTEGER,
    sk_id_curr INTEGER,
    feature_name TEXT NOT NULL,
    feature_value TEXT,
    shap_value REAL NOT NULL,
    contribution_direction TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prediction_id) REFERENCES predictions (prediction_id),
    FOREIGN KEY (sk_id_curr) REFERENCES customers (sk_id_curr)
);

CREATE TABLE IF NOT EXISTS rules (
    rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_text TEXT NOT NULL,
    risk_band TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_predictions_customer ON predictions (sk_id_curr);
CREATE INDEX IF NOT EXISTS idx_predictions_risk_band ON predictions (risk_band);
CREATE INDEX IF NOT EXISTS idx_shap_customer ON shap_outputs (sk_id_curr);
