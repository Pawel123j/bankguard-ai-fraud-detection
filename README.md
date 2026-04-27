# BankGuard AI — Fraud Detection Dashboard

BankGuard AI is a fullstack fintech portfolio project that simulates a fraud analyst dashboard for a bank. It combines transaction monitoring, fraud scoring, case management, API design, reporting, frontend dashboard design, backend tests, and a clean monorepo structure.

## Why This Project Matters

Fraud detection is a high-impact banking problem where analysts need fast signal, clear evidence, and reliable workflows. This project demonstrates how a bank-facing internal tool can ingest transactions, score risk, open fraud cases, and summarize operational exposure in a practical dashboard.

## Tech Stack

- Frontend: React, TypeScript, Vite, plain CSS
- Backend: Python, FastAPI, SQLAlchemy, Pydantic
- Database: SQLite
- Testing: pytest, FastAPI TestClient
- Tooling: optional Docker Compose, GitHub Actions CI example

## Features

- Demo analyst login
- Dashboard metrics for transactions, high-risk activity, critical alerts, and open cases
- Fraud scoring engine with analyst-readable reasons
- Transaction list with search, filtering, sorting, and detail view
- CSV transaction import
- Fraud case board with status updates and notes
- Reports summary with CSV and JSON export buttons
- SQLite database for local development without Docker
- Backend test coverage for fraud logic and core API endpoints

## Architecture

```text
bankguard-ai-fraud-detection/
  backend/   FastAPI API, SQLite models, fraud engine, seed script, tests
  frontend/  React TypeScript dashboard and API client
  .github/   CI workflow example for portfolio demonstration
```

The backend owns fraud scoring, persistence, API routes, CSV imports, dashboard aggregation, and report summaries. The frontend consumes the API through `frontend/src/api/client.ts` and presents an analyst-focused interface.

## Screenshots

![Dashboard Screenshot](docs/screenshots/dashboard.png)
![Transactions Screenshot](docs/screenshots/transactions.png)

## Demo Credentials

- Email: `analyst@bankguard.ai`
- Password: `demo123`

## How To Run The Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python seed.py
uvicorn app.main:app --reload
```

On Windows PowerShell:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python seed.py
uvicorn app.main:app --reload
```

The API will run at `http://localhost:8000`.

## How To Run The Frontend

```bash
cd frontend
npm install
npm run dev
```

The dashboard will run at `http://localhost:5173`.

## Seeding The Database

The seed file is located at `backend/data/sample_transactions.csv` and contains 50 realistic sample transactions across low, medium, high, and critical risk patterns.

```bash
cd backend
python seed.py
```

The seed script recreates the local SQLite tables, calculates fraud scores, and opens cases for high and critical transactions.

## API Endpoints

- `GET /health`
- `GET /api/dashboard/stats`
- `GET /api/transactions`
- `GET /api/transactions/{id}`
- `POST /api/transactions`
- `POST /api/transactions/import`
- `GET /api/cases`
- `PATCH /api/cases/{id}`
- `GET /api/reports/summary`
- `POST /api/auth/login`

## Fraud Scoring Rules

The scoring engine returns a risk score from 0 to 100, a risk level, and a reasons list.

- Amount over 10,000: +25
- Foreign transaction: +15
- Night transaction: +10
- Three or more previous failed attempts: +20
- Device trust score below 40: +20
- Suspicious merchant category: +10
- Unusual country or location: +10

Risk levels:

- 0-29: LOW
- 30-59: MEDIUM
- 60-79: HIGH
- 80-100: CRITICAL

## Tests

```bash
cd backend
pytest
```

## Optional Docker Compose

Docker is optional. The project is designed to run locally without containers.

```bash
docker compose up
```

## Portfolio Value

This project demonstrates:

- Fullstack development
- Fintech domain knowledge
- Fraud detection logic
- Dashboard design
- API design
- Testing
- Basic CI/CD

## Future Improvements

- Add authentication with JWT and role-based permissions
- Add model-based anomaly detection
- Add transaction velocity checks per customer
- Add audit logs for case updates
- Add pagination for larger datasets
- Add real charting with drill-down views
- Add PDF report generation

## Author

Pawel123j

