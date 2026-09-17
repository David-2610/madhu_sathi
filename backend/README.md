# Honey Chain – Backend

> **Phase 1 – Foundation only.**  
> No business logic, authentication, or domain models are implemented yet.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Virtual Environment Setup](#virtual-environment-setup)
3. [Dependency Installation](#dependency-installation)
4. [Environment Configuration](#environment-configuration)
5. [PostgreSQL Setup](#postgresql-setup)
6. [Starting the Server](#starting-the-server)
7. [API Documentation](#api-documentation)
8. [Running Tests](#running-tests)
9. [Project Structure](#project-structure)

---

## Prerequisites

| Tool | Minimum Version |
|------|----------------|
| Python | 3.11 |
| PostgreSQL | 14 |
| pip | 23+ |

Confirm your Python version:

```bash
python --version
```

---

## Virtual Environment Setup

```bash
# From the backend/ directory
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

---

## Dependency Installation

```bash
pip install -r requirements.txt
```

---

## Environment Configuration

```bash
# Copy the template
cp .env.example .env
```

Open `.env` and fill in your values:

```ini
APP_ENV=development
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/honeychain
SECRET_KEY=replace-with-a-long-random-string   # openssl rand -hex 32
```

> ⚠️ **Never commit `.env` to version control.** It is listed in `.gitignore`.

---

## PostgreSQL Setup

1. Install PostgreSQL 14+ if not already installed.
2. Start the PostgreSQL service.
3. Create the database:

```sql
-- Connect as superuser (psql -U postgres)
CREATE DATABASE honeychain;
```

4. Update `DATABASE_URL` in your `.env` with the correct credentials.

The application will probe the connection at startup and log a warning if it cannot connect (the process still starts).

---

## Starting the Server

```bash
# Development (auto-reload on code changes)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production-style (no reload)
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Expected startup output:

```
INFO  | app.main | Starting Honey Chain v0.1.0 [development]
INFO  | app.main | Database connection: OK
INFO  | uvicorn  | Application startup complete.
```

---

## API Documentation

Once the server is running:

| Interface | URL |
|-----------|-----|
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| OpenAPI JSON | http://localhost:8000/openapi.json |

### Endpoints (Phase 1)

```
GET /health   →  {"status": "ok"}
```

---

## Running Tests

```bash
pytest
```

Verbose output:

```bash
pytest -v
```

With coverage report (requires `pytest-cov`):

```bash
pip install pytest-cov
pytest --cov=app --cov-report=term-missing
```

---

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI application factory
│   ├── core/
│   │   └── config.py        # Settings loaded from .env
│   ├── db/
│   │   └── __init__.py      # SQLAlchemy engine, session, Base
│   └── api/
│       └── routes/
│           └── health.py    # GET /health
├── migrations/              # Alembic migration scripts (auto-generated)
│   └── versions/
├── tests/
│   ├── test_health.py
│   └── test_config.py
├── .env.example             # Environment variable template
├── .gitignore
├── alembic.ini              # Alembic configuration
├── pytest.ini
├── requirements.txt
└── README.md
```

---

## Database Migrations (Alembic)

Alembic is initialised and ready for Phase 2 models.

```bash
# Create a new migration after adding SQLAlchemy models
alembic revision --autogenerate -m "describe your change"

# Apply all pending migrations
alembic upgrade head

# Roll back the last migration
alembic downgrade -1
```
