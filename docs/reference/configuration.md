# Configuration

LACE is configured via environment variables. Copy `.env.example` to `.env` at the repo root and edit before starting.

---

## Required

| Variable | Description |
|---|---|
| `SECRET_KEY` | JWT signing key — minimum 32 characters, randomly generated |
| `DATABASE_URL` | SQLAlchemy connection string (see [Database](#database) below) |

---

## Optional — Application

| Variable | Default | Description |
|---|---|---|
| `FIRST_ADMIN_USERNAME` | `admin` | Username of the admin account created on first startup |
| `FIRST_ADMIN_PASSWORD` | — | Password for the auto-created admin; required on first startup |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifetime in minutes |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime in days |
| `CORS_ORIGINS` | `["http://localhost:3721"]` | JSON array of allowed CORS origins |
| `API_URL` | `http://localhost:8000` | Backend URL as seen by the frontend build |

---

## Optional — Security & Limits

| Variable | Default | Description |
|---|---|---|
| `PASSWORD_MIN_LENGTH` | `8` | Minimum password length |
| `PASSWORD_REQUIRE_DIGIT` | `false` | Require at least one digit in passwords |
| `PASSWORD_REQUIRE_LETTER` | `false` | Require at least one letter in passwords |
| `AUTH_RATE_LIMIT_REQUESTS` | `10` | Max login attempts per window |
| `AUTH_RATE_LIMIT_WINDOW_SECONDS` | `60` | Rate limit window duration in seconds |
| `MAX_UPLOAD_MB` | `10` | Maximum CSV upload size in megabytes |
| `MAX_IMPORT_ROWS` | — | Maximum number of rows per CSV import (unlimited if unset) |

---

## Database

### SQLite (development / single-host)

```
DATABASE_URL=sqlite:///./data/app.db
```

The file is created automatically. In Docker, mount the `data/` directory as a volume to persist it across restarts.

### PostgreSQL (production)

```
DATABASE_URL=postgresql://user:password@host:5432/dbname
```

!!! warning
    Never commit `.env` to version control. Use secrets management (e.g., Docker secrets, GitHub Actions secrets) in production deployments.
