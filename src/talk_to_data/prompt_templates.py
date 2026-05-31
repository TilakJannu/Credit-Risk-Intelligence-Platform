"""Schema-aware prompts for Gemini NL-to-SQL generation."""

from __future__ import annotations

from textwrap import dedent


SCHEMA_DESCRIPTION = """
Tables:
- customers(sk_id_curr, target, income_total, credit_amount, annuity, gender,
  education_type, family_status, occupation_type, housing_type, age_years,
  employment_years)
- predictions(prediction_id, sk_id_curr, default_probability, risk_score,
  risk_band, created_at)
- shap_outputs(shap_id, prediction_id, sk_id_curr, feature_name, feature_value,
  shap_value, contribution_direction, created_at)
- rules(rule_id, rule_text, risk_band, created_at)

Relationships:
- customers.sk_id_curr = predictions.sk_id_curr
- predictions.prediction_id = shap_outputs.prediction_id
- customers.sk_id_curr = shap_outputs.sk_id_curr
"""


FEW_SHOT_EXAMPLES = """
Question: Show top 10 high-risk customers.
SQL: SELECT c.sk_id_curr, p.default_probability, p.risk_band
FROM customers c
JOIN predictions p ON c.sk_id_curr = p.sk_id_curr
WHERE p.risk_band = 'HIGH'
ORDER BY p.default_probability DESC
LIMIT 10;

Question: Which occupation has the highest default rate?
SQL: SELECT occupation_type, AVG(target) AS default_rate, COUNT(*) AS applicant_count
FROM customers
WHERE occupation_type IS NOT NULL
GROUP BY occupation_type
ORDER BY default_rate DESC
LIMIT 10;

Question: What is the average income by risk band?
SQL: SELECT p.risk_band, AVG(c.income_total) AS average_income, COUNT(*) AS applicants
FROM predictions p
JOIN customers c ON c.sk_id_curr = p.sk_id_curr
GROUP BY p.risk_band
ORDER BY average_income DESC;

Question: How many customers are in each risk band?
SQL: SELECT risk_band, COUNT(*) AS customer_count
FROM predictions
GROUP BY risk_band
ORDER BY customer_count DESC;

Question: What is the average default probability for high-risk customers?
SQL: SELECT AVG(default_probability) AS avg_default_probability, COUNT(*) AS high_risk_customers
FROM predictions
WHERE risk_band = 'HIGH';

Question: Show the top 5 customers with the highest credit amount.
SQL: SELECT sk_id_curr, credit_amount, income_total
FROM customers
WHERE credit_amount IS NOT NULL
ORDER BY credit_amount DESC
LIMIT 5;

Question: What is the overall portfolio default rate?
SQL: SELECT AVG(target) AS portfolio_default_rate, COUNT(*) AS labeled_customers
FROM customers
WHERE target IS NOT NULL;
"""


def build_sql_prompt(question: str) -> str:
    """Build a hallucination-resistant SQL generation prompt."""
    return dedent(
        f"""
        You are a careful SQLite analyst for a credit risk platform.
        Generate exactly one SQLite SELECT query for the user's question.

        Rules:
        - Return SQL only, no markdown and no explanation.
        - Use only the tables and columns listed in the schema.
        - Do not invent tables or columns.
        - Do not use INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, PRAGMA, or CREATE.
        - Prefer explicit JOIN conditions.
        - Add LIMIT 100 unless an aggregate result or stricter limit is requested.

        Schema:
        {SCHEMA_DESCRIPTION}

        Examples:
        {FEW_SHOT_EXAMPLES}

        User question: {question}
        SQL:
        """,
    ).strip()


def build_insight_prompt(
    question: str,
    sql: str,
    rows_preview: str,
    row_count: int,
) -> str:
    """Build a prompt that turns validated SQL results into a business narrative."""
    return dedent(
        f"""
        You are a credit risk business analyst assistant.
        The user asked a question about a loan portfolio. A validated SQLite query was run.
        Write a clear, plain-English business answer using ONLY the query results below.

        Rules:
        - Do not invent numbers, customers, or trends that are not supported by the results.
        - If the result set is empty, say so and suggest what the user could check next.
        - Lead with the direct answer to the question in 1-2 sentences.
        - Add 2-4 short bullet points for key figures or patterns when helpful.
        - Use percentages with one decimal place when rates are shown.
        - Keep the tone professional and suitable for a credit committee or business analyst.
        - Do not include SQL, markdown headings, or code fences.

        User question: {question}

        SQL executed:
        {sql}

        Total rows returned: {row_count}

        Result preview (may be truncated):
        {rows_preview}

        Business answer:
        """,
    ).strip()
