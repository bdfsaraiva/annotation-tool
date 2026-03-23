# LACE — Labelling Adjacency and Conversation Entanglement

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**LACE** (*Labelling Adjacency and Conversation Entanglement*) is a full-stack web application for managing multi-annotator projects focused on:

- **Chat Disentanglement** — group conversation turns into threads
- **Adjacency Pairs** — create directed links between turns with typed relations

Designed for computational linguistics research requiring rigorous inter-annotator agreement (IAA) measurement.

---

## Table of Contents

- [Features](#features)
- [Quickstart (Docker)](#quickstart-docker)
- [Local Development](#local-development)
- [Configuration](#configuration)
- [Architecture](#architecture)
- [Data Format](#data-format)
- [Running Tests](#running-tests)
- [Citing This Work](#citing-this-work)
- [Contributing](#contributing)

---

## Features

| Feature | Description |
|---|---|
| **Multi-project** | Manage independent annotation projects with different types and settings |
| **Multi-annotator** | Assign multiple annotators per project; track individual progress |
| **Chat Disentanglement** | Assign turns to threads using text labels |
| **Adjacency Pairs** | Draw directed relation links with typed labels via drag or right-click |
| **CSV Import** | Import chat rooms from CSV with preview and validation |
| **JSON/ZIP Export** | Export annotations per room or per annotator |
| **IAA Analysis** | Pairwise inter-annotator agreement using the Hungarian algorithm |
| **Dark/Light Mode** | User-selectable theme |
| **Admin Dashboard** | Full project, user, and chat-room lifecycle management |
| **REST API** | Documented OpenAPI/Swagger interface at `/docs` |

---

## Quickstart (Docker)

**Requirements**: Docker ≥ 24, Docker Compose ≥ 2.

```bash
git clone https://github.com/YOUR_ORG/YOUR_REPO.git
cd YOUR_REPO
cp .env.example .env        # edit FIRST_ADMIN_USERNAME / FIRST_ADMIN_PASSWORD
docker compose up -d --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3721 |
| Backend API | http://localhost:8000 |
| Swagger docs | http://localhost:8000/docs |

---

## Local Development

### Backend (Python 3.11+)

```bash
cd annotation-backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend (Node 18+)

```bash
cd annotation_ui
npm install
npm start          # dev server → http://localhost:3721
```

---

## Configuration

Copy `.env.example` to `.env` and adjust:

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy URL — SQLite or PostgreSQL | `sqlite:///./data/app.db` |
| `SECRET_KEY` | JWT signing key (≥ 32 chars) | — |
| `FIRST_ADMIN_USERNAME` | Auto-created admin username | `admin` |
| `FIRST_ADMIN_PASSWORD` | Auto-created admin password | — |
| `CORS_ORIGINS` | JSON list of allowed origins | `["http://localhost:3721"]` |
| `API_URL` | Backend URL seen by the frontend | `http://localhost:8000` |
| `MAX_UPLOAD_MB` | Maximum CSV upload size | `10` |

---

## Architecture

```
annotation-backend/     FastAPI + SQLAlchemy (Python 3.11)
annotation_ui/          React 18 + Vite (Node 18)
conversion_tools/       CSV/Excel batch-import utilities (Python)
data/                   SQLite database (dev) / bind-mounted volume
docs/                   Architecture, operations, and screenshots
```
---

## Data Format

### Chat Room CSV

```csv
turn_id,user_id,turn_text,reply_to_turn
T001,user_a,"Hello everyone",
T002,user_b,"Hi! How are you?",T001
T003,user_a,"Doing well, thanks!",T002
```

| Column | Required | Description |
|---|---|---|
| `turn_id` | ✅ | Unique identifier for the turn |
| `user_id` | ✅ | Speaker identifier |
| `turn_text` | ✅ | Turn content |
| `reply_to_turn` | ❌ | `turn_id` of the turn being replied to |

A sample file is provided at [`docs/sample_chat_room.csv`](docs/sample_chat_room.csv).

---

## Running Tests

### Backend

```bash
cd annotation-backend
pytest --cov=app -v
```

### Frontend

```bash
cd annotation_ui
npm test -- --run    # single run
npm test             # watch mode
```

---

## Citing This Work

If you use LACE in your research, please use the metadata in [`CITATION.cff`](CITATION.cff).

---

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

- [Report a bug](../../issues/new?template=bug_report.md)
- [Request a feature](../../issues/new?template=feature_request.md)
