# Testing

## Backend

Tests use **pytest** with an in-memory SQLite database. Run from the `annotation-backend/` directory.

```bash
cd annotation-backend
pytest -v
```

With coverage:

```bash
pytest --cov=app -v
```

Test files live in `annotation-backend/tests/` and cover:

- Authentication and JWT flow
- Project and user CRUD
- CSV import validation
- Disentanglement annotation read/write
- Adjacency pair annotation read/write
- IAA computation
- Admin-only access guards

---

## Frontend

Tests use **Vitest**.

```bash
cd annotation_ui
npm test -- --run    # single run
npm test             # watch mode
```

---

## CI

GitHub Actions runs the backend test suite on every push and pull request. See `.github/workflows/backend-tests.yml`.
