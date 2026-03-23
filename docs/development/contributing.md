# Contributing

Contributions are welcome. Please read these guidelines before opening a pull request.

---

## Getting Started

1. Fork the repository and create a branch from `main`.
2. Follow the [Development Setup](setup.md) guide.
3. Make your changes, adding or updating tests where applicable.
4. Ensure all CI checks pass.
5. Open a pull request with a clear description.

---

## Code Style

=== "Backend"

    Python 3.11+. Formatted with `black`, linted with `ruff`:

    ```bash
    black annotation-backend/
    ruff check annotation-backend/
    ```

=== "Frontend"

    React + Vite. ESLint is configured in `package.json`:

    ```bash
    cd annotation_ui
    npm run lint
    ```

---

## Commit Messages

Use the imperative mood, short and descriptive:

```
Add CSV import preview endpoint
Fix thread colour assignment for >12 threads
Update Alembic migration for adjacency pairs
```

---

## Reporting Issues

- [Report a bug](https://github.com/bdfsaraiva/LACE/issues/new?template=bug_report.md)
- [Request a feature](https://github.com/bdfsaraiva/LACE/issues/new?template=feature_request.md)

---

## Licence

By contributing you agree that your contributions will be licensed under the [MIT Licence](https://github.com/bdfsaraiva/LACE/blob/main/LICENSE).
