#!/bin/sh

# Wait for the database to be ready
if echo "$DATABASE_URL" | grep -q "postgresql"; then
    echo "Waiting for PostgreSQL..."
    until python -c "
import sys, os
try:
    import psycopg2
    psycopg2.connect(os.environ['DATABASE_URL'])
    sys.exit(0)
except Exception as e:
    print(e)
    sys.exit(1)
" 2>&1; do
        echo "PostgreSQL not ready, retrying in 2s..."
        sleep 2
    done
    echo "PostgreSQL ready."
else
    sleep 2
fi

# Run database migrations
alembic upgrade head

# Start the FastAPI application
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
