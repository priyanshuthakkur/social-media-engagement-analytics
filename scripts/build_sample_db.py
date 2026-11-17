"""
build_sample_db.py
------------------
Loads the made-up sample snapshot in tests/fixtures/ into data/youtube.duckdb,
so the dbt models can be built and tested without a YouTube API key.
Used by CI and handy for trying the project out.

Usage:
    python scripts/build_sample_db.py
    cd dbt && dbt build && cd ..
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src import load_raw  # noqa: E402

SAMPLE_DIR = "tests/fixtures/sample_snapshot"

if __name__ == "__main__":
    load_raw.main(raw_dir=SAMPLE_DIR)
