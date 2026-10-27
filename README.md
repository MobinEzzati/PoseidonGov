# PoseidonGov

AI-powered deal-intelligence platform for PE firms evaluating aviation and
GovCon assets. PoseidonGov automates due diligence and risk scoring, cutting the
manual research time and error rate that slow down analyst decision-making.

MVP scope: PE deals in government contracting, focused on aviation and
construction. The architecture is built to generalize; the long-term goal is a
diligence engine for PE more broadly, not just this niche.

<img width="628" height="673" alt="PoseidonGov dashboard" src="https://github.com/user-attachments/assets/16c2f72c-7ef6-4df6-b35e-067519eb823a" />

## What it does
- Ingests federal procurement data (USASpending, SAM.gov, FAA aircraft registry)
- ML risk scoring: HHI revenue concentration + recompete risk
- AI-generated diligence memos via AWS Bedrock (Claude Sonnet)
- 160+ companies scored, 4,730 contracts, 316K aircraft records

## Stack
Python, FastAPI, Streamlit, PostgreSQL (pgvector), Docker, AWS (RDS, ECR, Bedrock, EC2)

## Run locally
```bash
cp .env.example .env            # local values for the docker-compose database
docker-compose up -d            # Postgres on localhost:5432
pip install -r requirements.txt
python scripts/db_setup/apply_schema.py   # create tables
uvicorn app.main:app --reload             # API on http://localhost:8000
streamlit run frontend/streamlit_app.py   # dashboard
```

Configuration is read from environment variables (see `.env.example`):
`DB_HOST`, `DB_USER`, `DB_PASSWORD`, and optionally `DB_PORT`, `DB_NAME`,
`DB_SSLMODE` (default `require`; use `disable` for the local Docker database).
Never commit `.env*` files other than `.env.example`.

## API
| Endpoint | Description |
| --- | --- |
| `GET /health` | Liveness check |
| `GET /companies` | Precomputed risk scores |
| `GET /companies/{name}/risk` | HHI, recompete risk, agency breakdown (404 if unknown) |
| `GET /companies/{name}/fleet` | Registered aircraft owned by the company |
| `GET /companies/{name}/memo` | AI diligence memo (404 if unknown) |

## Recompete risk model
`/risk` and the memo use an XGBoost model (`models/recompete_xgb_v1.json`) that
predicts whether an incumbent keeps a contract at recompete (risk = 1 - chance
kept, value-weighted over contracts ending within 24 months). It is trained on
about 1,000 labeled recompetes with hold-out AUC ~0.71 (0.59-0.78 across
time-ordered folds), so treat it as a relative ranking, not a probability.
It only knows 4 aircraft/defense NAICS codes and 47 contracting offices; when
under 70% of a company's contract value is familiar to it (or it has no
contract history), the API falls back to the rule-based score and says so in
`recompete_method`. Retrain with `python -m ml.train_recompete_xgb`.

## Project structure
```
app/         FastAPI service (main.py wires routers/, deps.py, db.py)
ml/          risk scoring, memo agent, recompete XGBoost training
ingestion/   pull USASpending / SAM.gov / FAA data into data/raw/
scripts/     db_setup/ (schema, DB creation), data_loads/ (load into Postgres), adhoc/ (one-off checks)
frontend/    Streamlit dashboard
db/          schema.sql
docs/        ARCHITECTURE.md (target design; the MVP is a subset)
data/        local raw downloads and logs (git-ignored)
poseidon-web Next.js frontend (not built yet)
```
Run Python modules from the repo root, e.g. `python -m ml.memo_agent`.

## CI/CD
Pushing to `main` runs `.github/workflows/continuous-integration.yml`, which
builds the Docker image and pushes it to Amazon ECR. The EC2 deploy step is
currently disabled in the workflow.

## Built by
Mobin Ezzati | MS Computer Science (AI/ML)
