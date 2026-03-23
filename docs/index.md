# LACE

**LACE** (*Labelling Adjacency and Conversation Entanglement*) is a full-stack web application for managing multi-annotator projects focused on conversational analysis.

It supports two annotation modes:

- **Chat Disentanglement** — group conversation turns into coherent threads
- **Adjacency Pairs** — draw directed, typed links between turns

Designed for computational linguistics research requiring rigorous inter-annotator agreement (IAA) measurement.

---

## Features

| Feature | Description |
|---|---|
| **Multi-project** | Manage independent annotation projects with different types and settings |
| **Multi-annotator** | Assign multiple annotators per project; track individual progress |
| **Chat Disentanglement** | Assign turns to threads using colour-coded labels |
| **Adjacency Pairs** | Draw directed relation links with typed labels via drag or right-click |
| **CSV Import** | Import chat rooms from CSV with row-level preview and validation |
| **JSON/ZIP Export** | Export annotations per room or per annotator |
| **IAA Analysis** | Pairwise inter-annotator agreement using the Hungarian algorithm |
| **Admin Dashboard** | Full project, user, and chat-room lifecycle management |
| **REST API** | OpenAPI/Swagger interface at `/docs` |

---

## Quickstart (Docker)

**Requirements**: Docker ≥ 24, Docker Compose ≥ 2.

```bash
git clone https://github.com/bdfsaraiva/LACE.git
cd lace
cp .env.example .env   # edit FIRST_ADMIN_USERNAME / FIRST_ADMIN_PASSWORD
docker compose up -d --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3721 |
| Backend API | http://localhost:8000 |
| Swagger docs | http://localhost:8000/docs |

The first admin account is created automatically from the `FIRST_ADMIN_USERNAME` and `FIRST_ADMIN_PASSWORD` values in `.env`.

---

## Further Reading

- [REST API](reference/api.md) — endpoint reference
- [Data Format](reference/data-format.md) — CSV input and export formats
- [Configuration](reference/configuration.md) — all environment variables
- [Architecture](development/architecture.md) — system design and database schema
- [Development Setup](development/setup.md) — run LACE locally without Docker
