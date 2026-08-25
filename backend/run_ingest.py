"""One-time (or repeatable) build step: run this after cloning to build the
SQLite DB and ChromaDB index from the raw data pack before starting the server."""
from app.ingest import build_index
from app.db import build_database

if __name__ == "__main__":
    print("Building SQLite database from xlsx...")
    build_database()
    print("Building ChromaDB document index...")
    build_index(reset=True)
    print("Done. You can now run: python -m app.main")
