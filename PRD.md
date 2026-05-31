# PRD.md

# Credit Risk Intelligence Platform

## Product Requirements Document (PRD)

Version: 1.0

Project Type: AI-Powered Credit Risk Intelligence System

Author: AI Engineer

---

# 1. Product Overview

The Credit Risk Intelligence Platform is an AI-powered decision-support system designed to help financial institutions assess loan applicant risk, understand model decisions, and explore credit data using natural language.

The platform combines machine learning, explainable AI, business rule generation, and conversational analytics into a single application.

The system uses the Home Credit Default Risk dataset to predict the likelihood of loan default while providing transparent explanations and business-friendly insights.

---

# 2. Problem Statement

Banks and financial institutions process thousands of loan applications and must determine whether an applicant is likely to repay a loan.

Traditional risk assessment processes suffer from:

* Manual review effort
* Limited explainability
* Slow decision making
* Difficulty analyzing large datasets
* Lack of business-friendly insights
* Regulatory transparency requirements

The platform aims to solve these challenges by automating risk prediction and providing explainable recommendations.

---

# 3. Product Goals

## Primary Goals

### Goal 1

Predict the probability that a loan applicant will default.

### Goal 2

Provide transparent explanations for every prediction.

### Goal 3

Generate business-readable risk rules.

### Goal 4

Enable natural-language access to credit data.

### Goal 5

Deliver a production-ready deployable solution.

---

# 4. Target Users

## Credit Risk Analysts

Responsible for assessing applicant risk.

Needs:

* Risk scores
* Default probability
* Applicant explanations

---

## Credit Managers

Responsible for approving or rejecting loans.

Needs:

* Business-friendly recommendations
* Risk summaries
* Decision rules

---

## Business Analysts

Responsible for portfolio analysis.

Needs:

* Natural language analytics
* Interactive dashboards
* Data exploration

---

## Auditors & Compliance Teams

Responsible for regulatory validation.

Needs:

* Explainability
* Decision transparency
* Rule traceability

---

# 5. Success Metrics

## Machine Learning

Target:

* ROC-AUC > 0.75
* Strong Recall
* Stable PR-AUC performance

---

## Explainability

Target:

* Explanation generated for 100% of predictions

---

## Talk-to-Data

Target:

* Successfully answer at least 10 predefined business questions

---

## Deployment

Target:

* Complete platform starts using:

```bash
docker-compose up
```

---

# 6. Core Features

## Feature 1: Dataset Exploration

### Description

Allow users to understand the dataset through visual analytics.

### Capabilities

* Missing value analysis
* Class imbalance analysis
* Demographic analysis
* Credit analysis
* Repayment behavior analysis

### Outputs

* Charts
* Summary statistics
* Business insights

---

## Feature 2: Credit Risk Prediction

### Description

Predict the likelihood of loan default.

### Inputs

Applicant information:

* Income
* Credit amount
* Annuity
* Employment history
* Bureau features
* Historical repayment data

### Outputs

```text
Default Probability

Risk Score

Risk Category
```

---

## Feature 3: Risk Classification

### Description

Convert default probability into business-friendly categories.

### Risk Bands

| Probability | Risk Band   |
| ----------- | ----------- |
| < 0.30      | Low Risk    |
| 0.30 - 0.60 | Medium Risk |
| > 0.60      | High Risk   |

---

## Feature 4: Explainable AI

### Description

Provide reasoning behind every model prediction.

### Outputs

* Top positive contributors
* Top negative contributors
* SHAP explanations
* Waterfall visualization
* Feature importance rankings

### User Value

Allows business users to understand why a customer was classified as risky.

---

## Feature 5: Business Rule Generation

### Description

Convert machine learning patterns into human-readable decision logic.

### Example

```text
IF income < 300000

AND overdue_payments > 2

THEN High Risk
```

### Benefits

* Audit support
* Compliance support
* Policy creation

---

## Feature 6: Talk-to-Data Assistant

### Description

Allow users to query platform data using natural language.

### Example Questions

```text
Which occupation has the highest default rate?

What is the average income of defaulters?

Which age group is most risky?

Show top 10 high-risk customers.

How does loan amount affect defaults?
```

### Workflow

```text
Question
    ↓
NL → SQL
    ↓
Database Query
    ↓
Business Answer
```

---

# 7. User Workflows

## Workflow A: Risk Prediction

```text
User Opens Platform
        ↓
Enter Applicant Details
        ↓
Submit
        ↓
Prediction Generated
        ↓
Risk Score Displayed
        ↓
Explanation Displayed
```

---

## Workflow B: Explainability

```text
Prediction
      ↓
View Explanation
      ↓
Feature Contributions
      ↓
Business Interpretation
```

---

## Workflow C: Natural Language Analytics

```text
User Question
       ↓
NL → SQL
       ↓
Database Query
       ↓
Results
       ↓
Readable Business Insight
```

---

# 8. Functional Requirements

## FR-01

The system shall load Home Credit datasets.

---

## FR-02

The system shall clean and preprocess data before training.

---

## FR-03

The system shall train multiple machine learning models.

---

## FR-04

The system shall generate default probability predictions.

---

## FR-05

The system shall classify applicants into risk categories.

---

## FR-06

The system shall generate SHAP explanations.

---

## FR-07

The system shall generate business-readable decision rules.

---

## FR-08

The system shall convert natural language questions into SQL queries.

---

## FR-09

The system shall validate generated SQL before execution.

---

## FR-10

The system shall display all outputs through a web-based dashboard.

---

## FR-11

The system shall support Dockerized deployment.

---

# 9. Non-Functional Requirements

## Performance

Prediction response time:

```text
< 3 seconds
```

---

## Reliability

Prediction consistency across repeated requests.

---

## Security

Only read-only SQL execution permitted.

Blocked:

```text
DELETE
DROP
UPDATE
INSERT
ALTER
```

---

## Scalability

Architecture should support future migration to PostgreSQL and cloud deployment.

---

## Maintainability

Code must follow the prescribed project structure.

---

# 10. Dashboard Modules

## Module 1

Executive Dashboard

Displays:

* Total Applicants
* Default Rate
* Risk Distribution

---

## Module 2

EDA Dashboard

Displays:

* Demographics
* Financial Analysis
* Credit Analysis

---

## Module 3

Risk Prediction

Displays:

* Risk Score
* Risk Band
* Default Probability

---

## Module 4

Explainability

Displays:

* SHAP Charts
* Feature Contributions

---

## Module 5

Business Rules

Displays:

* Generated Rules
* Decision Logic

---

## Module 6

AI Data Analyst

Displays:

* Chat Interface
* Query Results
* Business Insights

---

# 11. Assumptions

* Home Credit dataset is available locally.
* Users have access to modern browsers.
* Docker is installed on deployment environment.
* Gemini API key is available through environment variables.

---

# 12. Future Enhancements

* LightGBM integration
* Real-time scoring API
* Portfolio risk monitoring
* Model drift detection
* PostgreSQL migration
* PDF credit assessment reports
* Multi-language analytics
* Role-based access control

---

# 13. Definition of Success

The product is considered successful when:

✓ Credit default prediction works accurately

✓ Risk bands are generated correctly

✓ SHAP explanations are available

✓ Business rules are generated

✓ Natural language analytics works reliably

✓ Dashboard is fully functional

✓ Docker deployment succeeds

✓ All NeoStats assignment requirements are satisfied
