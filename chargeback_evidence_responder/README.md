# 🛡️ Chargeback Evidence Responder
### AI Risk Manager | Razorpay Internship Hackathon 2026

---

## 📌 Problem Statement

Every year, merchants lose billions to chargebacks — and the fight-back process is broken.
When a customer disputes a transaction, the merchant has a narrow window (often 7 days) to
assemble documentary evidence, write a formal rebuttal letter, and submit representment to
the acquiring bank. Most small and mid-sized merchants either skip the fight entirely
(guaranteed loss of goods **and** money) or fight blindly, spending ₹2,300+ of fees and
manual effort on cases they were always going to lose. There is no intelligent triage layer:
no way to know *which* disputes are worth fighting, *what* evidence would actually move the
needle, or *how* to phrase the response so the adjudicating bank takes it seriously.

The result is a silent tax on Indian e-commerce: unwinnable cases get fought (wasted effort),
winnable cases get surrendered (lost revenue + ₹1,500 chargeback fee each), and every letter
is written from scratch under deadline pressure by people who would rather be running their
business.

## 💡 Solution Overview

**Chargeback Evidence Responder** is an AI-powered decision engine that sits between the
chargeback notification and the merchant's response. It ingests dispute details, predicts
the probability of winning with an XGBoost classifier trained on 50,000 chargeback outcomes,
audits the available evidence across 9 proof types, explains its reasoning in plain English,
and generates a court-grade rebuttal letter as a downloadable Word document — in seconds.

```
                        ┌─────────────────────────────────────────────┐
                        │            CHARGEBACK INPUT (JSON/UI)       │
                        └───────────────────┬─────────────────────────┘
                                            │
              ┌─────────────────────────────▼─────────────────────────────┐
              │                   FEATURE ENGINEERING                     │
              │   27 features: amount tier · trust score · verification   │
              │   score · recency buckets · payment risk · encodings      │
              └──────────────┬────────────────────────┬───────────────────┘
                             │                        │
        ┌────────────────────▼─────────┐   ┌──────────▼──────────────────┐
        │   XGBOOST WIN-PROBABILITY    │   │    EVIDENCE ENGINE          │
        │   50k synthetic outcomes     │   │   9 proof types audited     │
        │   cost-tuned threshold 0.76  │   │   STRONG/MODERATE/WEAK      │
        └──────────────┬───────────────┘   └──────────┬──────────────────┘
                       │                              │
              ┌────────▼──────────────────────────────▼────────┐
              │            SHAP EXPLAINABILITY LAYER           │
              │   "+3DS verified (+18 pts) · no signed POD (−4)"│
              └──────────────────────┬─────────────────────────┘
                                     │
                 ┌───────────────────▼────────────────────┐
                 │      REBUTTAL LETTER GENERATOR          │
                 │   4 reason-code templates · .docx out   │
                 │   deadline urgency · Without Prejudice  │
                 └───────────────────┬────────────────────┘
                                     │
        ┌───────────────┬────────────▼───────────┬──────────────────┐
        ▼               ▼                        ▼                  ▼
  FastAPI /analyze  Streamlit           SQLite prediction     Rebuttal letter
  FIGHT/REVIEW/SKIP dashboard          & outcome history     (.docx download)
```

## ✨ Key Features

- 🎯 **Win-probability scoring** — XGBoost classifier, early-stopped, ROC-AUC 0.77 on held-out test data
- ⚖️ **Business-cost optimisation** — decision threshold tuned against real rupee costs, not abstract F1 alone
- 📦 **Evidence audit** — 9 proof types scored for completeness, Tier-1 gap detection, benchmark vs won cases
- 🧠 **SHAP explainability** — every score ships with "why", in language a merchant (not a data scientist) understands
- ✉️ **One-click rebuttal letters** — 4 legal-tone templates mapped to reason codes, filled with live metadata, exported to .docx
- ⏰ **Deadline urgency detection** — flags responses due within 72 hours
- 🔌 **REST API** — `POST /analyze`, `GET /metrics`, `GET /health`, `GET /download-letter/{id}`
- 📊 **Operator dashboard** — live analyzer, model performance, batch CSV scoring, win/loss history
- 🗄️ **Full audit trail** — every prediction, recommendation and evidence snapshot persisted to SQLite

## 🛠️ Tech Stack

| Layer | Technology | Why |
|---|---|---|
| ML Model | XGBoost 2.1.1 | Best-in-class tabular learner, native early stopping |
| Baseline | scikit-learn LogisticRegression | Interpretable benchmark (AUC 0.758) |
| Explainability | SHAP 0.46.0 | TreeExplainer gives exact per-case attributions |
| Dataset | pandas + numpy | 50,000-row synthetic corpus, fully reproducible (seed 42) |
| API | FastAPI + Pydantic v2 | Typed request/response contracts, auto OpenAPI docs |
| Dashboard | Streamlit + Plotly | Rapid operator UI, interactive charts |
| Persistence | SQLAlchemy 2.0 + SQLite | Zero-config audit trail |
| Letters | python-docx | In-memory Word document generation |
| Config | pyyaml + loguru | Single source of truth + structured logging |

## 🚀 Installation & Setup

```bash
# 1. Clone / enter the project
cd "d:\ochrestra\razor hacka"

# 2. Create a virtual environment (Python 3.12 recommended)
python -m venv .venv

# 3. Activate it
.\.venv\Scripts\activate          # Windows PowerShell
# source .venv/bin/activate       # Linux/macOS

# 4. Install pinned dependencies
pip install -r chargeback_evidence_responder\requirements.txt
```

> **Note:** the pins require Python ≤3.12 (`numpy 1.26.4` has no wheels for 3.13+).

## ▶️ How to Run

```bash
cd chargeback_evidence_responder

# One-shot: generate → preprocess → train → evaluate → explain → sample case
python run_all.py

# Or step by step:
python data/generator.py          # 1. regenerate the 50k synthetic dataset
python run_training.py            # 2. train XGBoost + tune threshold
python model/evaluator.py         # 3. full evaluation + plots + report
python model/explainer.py         # 4. SHAP global plots + sample narratives

# Launch the API  → http://127.0.0.1:8000  (docs at /docs)
uvicorn api.main:app --reload --port 8000

# Launch the dashboard → http://localhost:8501
streamlit run dashboard/app.py
```

## 📈 Model Performance

Measured on the held-out 20% test split (10,000 samples, threshold 0.76):

| Metric | Value |
|---|---|
| Precision | **0.8383** |
| Recall | **0.9873** |
| F1 Score | **0.9067** |
| ROC-AUC | **0.7662** |
| Average Precision (PR-AUC) | **0.9302** |
| False positives (fought but lost) | 1,581 cases |
| **Total false-positive cost** | **₹36,36,300** |
| Net value recovered (80% recovery on wins) | **₹5,57,26,000** |
| **ROI on fighting** | **+1432%** |

Per reason code (test set): CB001 unauthorized P=0.88/R=1.00 · CB002 non-receipt P=0.79/R=0.98 ·
CB003 not-as-described P=0.70/R=0.94 · CB004 friendly fraud P=0.90/R=1.00.

*Sample output:* running `python model/explainer.py` prints narratives like —

> "This chargeback has a HIGH chance of being won in your favour (about 95%). Main strengths:
> nearly all possible evidence is on file for this order; merchants historically win this type
> of dispute often. Risk factors: there is no signed receipt for this order."

Plots land in `model/artifacts/plots/` (ROC, PR, cost-vs-threshold, confusion matrix, 3 SHAP charts)
alongside `model/artifacts/evaluation_report.txt`.

## 📁 Project Structure

```
chargeback_evidence_responder/
├── data/
│   ├── generator.py           # Synthetic dataset creator (50k rows, seed 42)
│   ├── preprocessor.py        # Fit-on-train feature engineering (27 features)
│   └── chargebacks_synthetic.csv
├── model/
│   ├── trainer.py             # XGBoost training + threshold optimisation
│   ├── evaluator.py           # ML + ₹ business metrics, plots, report
│   ├── explainer.py           # SHAP narratives + global plots
│   └── artifacts/             # model.pkl · preprocessor.pkl · plots/
├── evidence/
│   ├── collector.py           # Simulated evidence gathering + metadata
│   └── scorer.py              # Completeness, strength, gap analysis
├── responder/
│   ├── letter_generator.py    # Template filling + docx rendering
│   └── templates/             # unauthorized / non_receipt / not_as_described / friendly_fraud
├── api/                       # FastAPI app, schemas, routes
├── dashboard/                 # Streamlit operator UI
├── utils/                     # logger (loguru) + db (SQLAlchemy)
├── tests/test_integration.py  # 8 pytest integration tests
├── config.yaml                # All thresholds, costs and weights
├── run_all.py                 # End-to-end pipeline runner
└── requirements.txt           # Pinned versions
```

## 🏆 Why This Wins

- **Defence-only by design.** This is not another fraud-detection tool that flags customers.
  It defends legitimate merchants after a false fraud claim — an underserved, high-pain space.
- **Costs in rupees, not abstractions.** Every recommendation is priced: fighting costs
  ₹2,300/case when you lose, skipping surrenders 30% of the transaction value. The threshold
  itself was chosen to minimise total rupee cost, and the ROI (+1432%) is measured, not claimed.
- **Built for Indian BFSI context.** ₹ amounts, INR formatting, British-English legal drafting,
  "Without Prejudice" convention, Razorpay Dispute Portal sign-off, UPI/netbanking payment rails.
- **Explainable or it didn't happen.** Banks and merchants will not act on a black box; every
  score arrives with its top drivers in plain English.
- **End-to-end in one click.** From raw CSV to a signed, deadline-aware, downloadable rebuttal
  letter — no human touches a template.

## 👥 Team / Author

**Author:** Shrey — AI Risk Manager track, Razorpay Internship Hackathon 2026

Built with an obsessive focus on honest numbers: every metric in this README is reproduced by
`run_all.py`, and every claim can be verified via `pytest tests/test_integration.py -v`.

---

*Generated artifacts (CSV, model.pkl, plots, logs) are gitignored — regenerate everything with
`python run_all.py`.*
