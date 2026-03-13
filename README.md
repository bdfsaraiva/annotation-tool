# Annotation Tool for Chat Disentanglement and Adjacency Pairs

Full‑stack web application to manage annotation projects, assign annotators, and collect:
- **Chat disentanglement** annotations (thread grouping)
- **Adjacency pairs** annotations (directed links between turns + relation type)

## Features
- Admin dashboard: projects, users, chat rooms, exports
- Annotator UI: fast turn annotation and linking
- Import chat rooms from CSV
- Export annotations (JSON) and adjacency pairs (TXT/ZIP)
- Built‑in IAA analysis for disentanglement

## Architecture
- **Backend**: FastAPI + SQLAlchemy + Alembic
- **Frontend**: React
- **Database**: SQLite (default)

## Quickstart (Docker)
```bash
cp .env.example .env
docker compose up -d --build
```

Open:
- Frontend: `http://localhost:3721`
- Backend API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

Default admin:
- `admin` / `admin`

## Configuration
The only required config is `SERVER_IP` in `.env`:
- Local: `SERVER_IP=localhost`
- LAN: `SERVER_IP=192.168.1.100`

This controls both frontend API URL and backend CORS.

## Data Import
### Chat rooms (CSV)
Upload via **Admin → Project → Import CSV**.

Required columns:
```
turn_id,user_id,turn_text,reply_to_turn
```

### Conversion tools (Excel → API)
```
cd conversion_tools
pip install -r requirements.txt
python import_excel.py
```

## Exports
### Disentanglement (JSON)
Admin → Project → Chat room → Export  
Includes full messages + annotations for all users.

### Adjacency pairs (TXT/ZIP)
Admin → Project → Chat room → Export  
Format per line:
```
turnA,turnB,relation_type
```
If exporting **all users**, a ZIP is returned with one file per annotator.

## Development
### Backend
```
cd annotation-backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend
```
cd annotation_ui
npm install
npm start
```

## Repository Layout
```
annotation-backend/     FastAPI backend + Alembic migrations
annotation_ui/          React frontend
conversion_tools/       Excel import utilities
docker-compose.yml
```

## License
MIT License. See `LICENSE`.

## Citation
See `CITATION.cff`.
