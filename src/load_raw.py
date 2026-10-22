"""
load_raw.py
-----------
Flattens the latest raw JSON snapshot from data/raw/ into two tables in a
local DuckDB database (data/youtube.duckdb):

    raw.channels  one row per channel per snapshot
    raw.videos    one row per video per snapshot

Only light reshaping happens here (nested JSON -> columns, ISO 8601
durations -> seconds). Business logic such as engagement rate lives in the
dbt models, so it is versioned, tested and documented in one place.

DuckDB stands in for a cloud warehouse such as BigQuery: same SQL and same
dbt models, no cloud account needed.

Usage:
    python src/load_raw.py
"""
import json
import os
import re

import pandas as pd

RAW_DIR = "data/raw"
DB_PATH = "data/youtube.duckdb"

DURATION_PATTERN = re.compile(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")


def parse_duration(iso_duration: str | None) -> int | None:
    """Convert an ISO 8601 duration such as 'PT1H2M3S' into seconds."""
    if not iso_duration:
        return None
    match = DURATION_PATTERN.fullmatch(iso_duration)
    if not match:
        return None
    days, hours, minutes, seconds = (int(part or 0) for part in match.groups())
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def to_int(value) -> int | None:
    """API counts arrive as strings and are missing when hidden (e.g. likes turned off)."""
    return int(value) if value is not None else None


def flatten_channels(raw: list[dict], snapshot_date: str) -> pd.DataFrame:
    rows = [
        {
            "channel_id": c["id"],
            "channel_title": c["snippet"]["title"],
            "handle": c["snippet"].get("customUrl"),
            "country": c["snippet"].get("country"),
            "subscriber_count": to_int(c["statistics"].get("subscriberCount")),
            "total_views": to_int(c["statistics"].get("viewCount")),
            "video_count": to_int(c["statistics"].get("videoCount")),
            "snapshot_date": snapshot_date,
        }
        for c in raw
    ]
    return pd.DataFrame(rows)


def flatten_videos(raw: list[dict], snapshot_date: str) -> pd.DataFrame:
    rows = [
        {
            "video_id": v["id"],
            "channel_id": v["snippet"]["channelId"],
            "title": v["snippet"]["title"],
            "published_at": v["snippet"]["publishedAt"],
            "duration_seconds": parse_duration(v["contentDetails"].get("duration")),
            "view_count": to_int(v["statistics"].get("viewCount")),
            "like_count": to_int(v["statistics"].get("likeCount")),
            "comment_count": to_int(v["statistics"].get("commentCount")),
            "tags": "|".join(v["snippet"].get("tags", [])),
            "snapshot_date": snapshot_date,
        }
        for v in raw
    ]
    df = pd.DataFrame(rows)
    if not df.empty:
        df["published_at"] = pd.to_datetime(df["published_at"], utc=True)
    return df


def latest_snapshot(raw_dir: str = RAW_DIR) -> str:
    snapshots = sorted(d for d in os.listdir(raw_dir) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d))
    if not snapshots:
        raise SystemExit("No snapshots in data/raw/. Run src/fetch_youtube.py first.")
    return snapshots[-1]


def main() -> None:
    import duckdb  # imported here so the tests above don't need it installed

    snapshot = latest_snapshot()
    folder = os.path.join(RAW_DIR, snapshot)
    with open(os.path.join(folder, "channels.json")) as f:
        channels = flatten_channels(json.load(f), snapshot)
    with open(os.path.join(folder, "videos.json")) as f:
        videos = flatten_videos(json.load(f), snapshot)

    con = duckdb.connect(DB_PATH)
    try:
        con.execute("CREATE SCHEMA IF NOT EXISTS raw")
        con.register("channels_df", channels)
        con.register("videos_df", videos)
        con.execute("CREATE OR REPLACE TABLE raw.channels AS SELECT * FROM channels_df")
        con.execute("CREATE OR REPLACE TABLE raw.videos AS SELECT * FROM videos_df")
    finally:
        con.close()

    print(f"Loaded snapshot {snapshot}: {len(channels)} channels, {len(videos)} videos -> {DB_PATH}")


if __name__ == "__main__":
    main()
