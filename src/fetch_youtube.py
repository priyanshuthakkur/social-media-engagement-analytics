"""
fetch_youtube.py
----------------
Pulls channel and video data from the YouTube Data API v3 for every channel
listed in config/channels.yml, and saves the raw API responses as JSON
snapshots in data/raw/<YYYY-MM-DD>/.

Raw responses are stored untouched on purpose: cleaning happens later (in
load_raw.py and the dbt models), so the original data can always be
re-processed without calling the API again.

Quota: each run costs roughly 1 unit per channel + 1 unit per 50 videos,
far below the free daily limit of 10,000 units.

Usage:
    python src/fetch_youtube.py
"""
import json
import os
import time
from datetime import date

import requests
import yaml
from dotenv import load_dotenv

API_URL = "https://www.googleapis.com/youtube/v3"
CONFIG_PATH = "config/channels.yml"
RAW_DIR = "data/raw"
BATCH_SIZE = 50  # max ids per videos.list call

# Temporary problems worth retrying: rate limiting and server-side errors.
# Anything else (e.g. 400 bad request, 403 quota exceeded) won't fix itself
# by retrying, so it fails straight away.
RETRY_STATUSES = {429, 500, 502, 503, 504}
MAX_ATTEMPTS = 3
BACKOFF_SECONDS = 2  # waits 2s, then 4s between attempts


def api_get(endpoint: str, params: dict, api_key: str) -> dict:
    """Call one YouTube API endpoint, retrying temporary failures, and fail loudly otherwise."""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.get(
                f"{API_URL}/{endpoint}", params={**params, "key": api_key}, timeout=30
            )
        except (requests.ConnectionError, requests.Timeout) as error:
            if attempt == MAX_ATTEMPTS:
                raise RuntimeError(
                    f"Could not reach the YouTube API on {endpoint} after {MAX_ATTEMPTS} attempts"
                ) from error
        else:
            if response.status_code == 200:
                return response.json()
            if response.status_code not in RETRY_STATUSES or attempt == MAX_ATTEMPTS:
                raise RuntimeError(
                    f"YouTube API error {response.status_code} on {endpoint}: {response.text[:300]}"
                )
        wait = BACKOFF_SECONDS * 2 ** (attempt - 1)
        print(f"  ...temporary problem on {endpoint}, retrying in {wait}s")
        time.sleep(wait)
    raise AssertionError("unreachable")


def get_channel(handle: str, api_key: str) -> dict | None:
    """Look up a channel by its @handle. Returns None if it doesn't exist."""
    data = api_get(
        "channels",
        {"part": "snippet,statistics,contentDetails", "forHandle": handle},
        api_key,
    )
    items = data.get("items", [])
    return items[0] if items else None


def get_upload_ids(uploads_playlist_id: str, max_videos: int, api_key: str) -> list[str]:
    """Page through a channel's uploads playlist and collect video ids (newest first)."""
    video_ids: list[str] = []
    page_token = None
    while len(video_ids) < max_videos:
        params = {"part": "contentDetails", "playlistId": uploads_playlist_id, "maxResults": 50}
        if page_token:
            params["pageToken"] = page_token
        data = api_get("playlistItems", params, api_key)
        video_ids += [item["contentDetails"]["videoId"] for item in data.get("items", [])]
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return video_ids[:max_videos]


def chunk(items: list, size: int) -> list[list]:
    """Split a list into consecutive chunks of at most `size` items."""
    return [items[i : i + size] for i in range(0, len(items), size)]


def get_videos(video_ids: list[str], api_key: str) -> list[dict]:
    """Fetch details and statistics for videos, 50 ids per request."""
    videos: list[dict] = []
    for batch in chunk(video_ids, BATCH_SIZE):
        data = api_get(
            "videos",
            {"part": "snippet,statistics,contentDetails", "id": ",".join(batch)},
            api_key,
        )
        videos += data.get("items", [])
    return videos


def main() -> None:
    load_dotenv()
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        raise SystemExit("YOUTUBE_API_KEY is missing. Copy .env.example to .env and add your key.")

    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    out_dir = os.path.join(RAW_DIR, date.today().isoformat())
    os.makedirs(out_dir, exist_ok=True)

    channels, videos = [], []
    for handle in config["channels"]:
        channel = get_channel(handle, api_key)
        if channel is None:
            print(f"  ! {handle}: channel not found, skipping (check the handle in channels.yml)")
            continue
        uploads_id = channel["contentDetails"]["relatedPlaylists"]["uploads"]
        ids = get_upload_ids(uploads_id, config["max_videos_per_channel"], api_key)
        channel_videos = get_videos(ids, api_key)
        channels.append(channel)
        videos += channel_videos
        print(f"  {handle}: {len(channel_videos)} videos")

    for name, payload in [("channels", channels), ("videos", videos)]:
        with open(os.path.join(out_dir, f"{name}.json"), "w") as f:
            json.dump(payload, f, indent=2)

    print(f"Saved {len(channels)} channels and {len(videos)} videos to {out_dir}/")


if __name__ == "__main__":
    main()
