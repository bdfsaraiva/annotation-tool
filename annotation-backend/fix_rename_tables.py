"""
One-time script to rename annotation tables to match current SQLAlchemy models.
Run on the Render backend shell: python fix_rename_tables.py
"""
import os
import sys
from sqlalchemy import create_engine, text, inspect

db_url = os.environ.get("DATABASE_URL")
if not db_url:
    print("ERROR: DATABASE_URL not set")
    sys.exit(1)

engine = create_engine(db_url)

with engine.connect() as conn:
    existing = inspect(engine).get_table_names()
    print("Current tables:", existing)

    renamed = []

    if "annotations" in existing and "disentanglement_annotation" not in existing:
        conn.execute(text("ALTER TABLE annotations RENAME TO disentanglement_annotation"))
        print("Renamed: annotations -> disentanglement_annotation")
        renamed.append("annotations")
    elif "disentanglement_annotation" in existing:
        print("disentanglement_annotation already exists, skipping")
    else:
        print("WARNING: 'annotations' table not found")

    if "adjacency_pairs" in existing and "adj_pairs_annotation" not in existing:
        conn.execute(text("ALTER TABLE adjacency_pairs RENAME TO adj_pairs_annotation"))
        print("Renamed: adjacency_pairs -> adj_pairs_annotation")
        renamed.append("adjacency_pairs")
    elif "adj_pairs_annotation" in existing:
        print("adj_pairs_annotation already exists, skipping")
    else:
        print("WARNING: 'adjacency_pairs' table not found")

    if renamed:
        conn.commit()
        print("Committed.")
    else:
        print("Nothing to rename.")

    print("Tables after:", inspect(engine).get_table_names())
