"""
Runs the ingestion stage end to end: fetch from the YouTube API, then load
the snapshot into DuckDB. The dbt models (stage 2, in progress) will build
on these raw tables.

Usage:
    python run_ingest.py
"""
from src import fetch_youtube, load_raw

if __name__ == "__main__":
    print("1/2 Fetching from the YouTube Data API...")
    fetch_youtube.main()
    print("2/2 Loading into DuckDB...")
    load_raw.main()
    print("Done. Raw tables raw.channels and raw.videos are ready in data/youtube.duckdb.")
