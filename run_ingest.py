"""
Runs the ingestion stage end to end: fetch from the YouTube API, then load
the snapshot into DuckDB. The dbt models (dbt/) take over from here.

Usage:
    python run_ingest.py
"""
from src import fetch_youtube, load_raw

if __name__ == "__main__":
    print("1/2 Fetching from the YouTube Data API...")
    fetch_youtube.main()
    print("2/2 Loading into DuckDB...")
    load_raw.main()
    print("Done. Next: cd dbt && dbt build")
