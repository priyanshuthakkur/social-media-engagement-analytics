"""
Tests for the ingestion stage. They use small mock API payloads, so no API
key, network access or database is needed.

Run with:  pytest
"""
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.fetch_youtube import api_get, chunk, get_upload_ids
from src.load_raw import flatten_channels, flatten_videos, parse_duration

MOCK_CHANNEL = {
    "id": "UC123",
    "snippet": {"title": "Test Brand", "customUrl": "@testbrand", "country": "GB"},
    "statistics": {"subscriberCount": "1500", "viewCount": "90000", "videoCount": "2"},
    "contentDetails": {"relatedPlaylists": {"uploads": "UU123"}},
}

MOCK_VIDEOS = [
    {
        "id": "vid1",
        "snippet": {
            "channelId": "UC123",
            "title": "Leg day routine",
            "publishedAt": "2026-09-01T17:30:00Z",
            "tags": ["fitness", "legs"],
        },
        "contentDetails": {"duration": "PT8M15S"},
        "statistics": {"viewCount": "1000", "likeCount": "50", "commentCount": "5"},
    },
    {
        # A Short with likes hidden and no tags: the fields are simply missing
        "id": "vid2",
        "snippet": {
            "channelId": "UC123",
            "title": "Quick tip",
            "publishedAt": "2026-09-02T08:00:00Z",
        },
        "contentDetails": {"duration": "PT45S"},
        "statistics": {"viewCount": "300"},
    },
]


def test_parse_duration_handles_common_formats():
    assert parse_duration("PT45S") == 45
    assert parse_duration("PT8M15S") == 495
    assert parse_duration("PT1H2M3S") == 3723
    assert parse_duration("P1DT1S") == 86401
    assert parse_duration("PT10M") == 600


def test_parse_duration_handles_missing_or_bad_values():
    assert parse_duration(None) is None
    assert parse_duration("") is None
    assert parse_duration("not-a-duration") is None


def test_chunk_splits_into_batches_of_50():
    batches = chunk(list(range(120)), 50)
    assert [len(b) for b in batches] == [50, 50, 20]


def test_flatten_channels_converts_counts_to_numbers():
    df = flatten_channels([MOCK_CHANNEL], "2026-10-22")
    row = df.iloc[0]
    assert row["channel_id"] == "UC123"
    assert row["subscriber_count"] == 1500
    assert row["snapshot_date"] == "2026-10-22"


def test_flatten_videos_handles_hidden_stats_and_missing_tags():
    df = flatten_videos(MOCK_VIDEOS, "2026-10-22").set_index("video_id")
    assert df.loc["vid1", "duration_seconds"] == 495
    assert df.loc["vid1", "like_count"] == 50
    assert df.loc["vid1", "tags"] == "fitness|legs"
    assert df.loc["vid2", "duration_seconds"] == 45
    assert df.loc["vid2", "tags"] == ""
    # hidden likes/comments must stay missing, not become 0 (that would skew engagement rates)
    assert df["like_count"].isna().sum() == 1
    assert df["comment_count"].isna().sum() == 1


def test_get_upload_ids_follows_pagination_and_respects_limit():
    pages = [
        {"items": [{"contentDetails": {"videoId": f"a{i}"}} for i in range(50)], "nextPageToken": "p2"},
        {"items": [{"contentDetails": {"videoId": f"b{i}"}} for i in range(50)]},
    ]
    with patch("src.fetch_youtube.api_get", side_effect=pages) as mock_get:
        ids = get_upload_ids("UU123", max_videos=70, api_key="fake")
    assert len(ids) == 70
    assert ids[0] == "a0" and ids[-1] == "b19"
    assert mock_get.call_count == 2


def fake_response(status: int, payload: dict | None = None) -> MagicMock:
    response = MagicMock(status_code=status, text="error details")
    response.json.return_value = payload or {}
    return response


@patch("src.fetch_youtube.time.sleep")
def test_api_get_retries_temporary_errors_then_succeeds(mock_sleep):
    responses = [fake_response(503), fake_response(200, {"items": ["ok"]})]
    with patch("src.fetch_youtube.requests.get", side_effect=responses) as mock_get:
        data = api_get("videos", {}, api_key="fake")
    assert data == {"items": ["ok"]}
    assert mock_get.call_count == 2
    mock_sleep.assert_called_once_with(2)


@patch("src.fetch_youtube.time.sleep")
def test_api_get_retries_network_errors(mock_sleep):
    side_effects = [requests.ConnectionError(), fake_response(200, {"items": []})]
    with patch("src.fetch_youtube.requests.get", side_effect=side_effects):
        assert api_get("videos", {}, api_key="fake") == {"items": []}


@patch("src.fetch_youtube.time.sleep")
def test_api_get_does_not_retry_permanent_errors(mock_sleep):
    # 403 (e.g. quota exceeded) won't fix itself, so it should fail straight away
    with patch("src.fetch_youtube.requests.get", return_value=fake_response(403)) as mock_get:
        with pytest.raises(RuntimeError, match="403"):
            api_get("videos", {}, api_key="fake")
    assert mock_get.call_count == 1
    mock_sleep.assert_not_called()


@patch("src.fetch_youtube.time.sleep")
def test_api_get_gives_up_after_max_attempts(mock_sleep):
    with patch("src.fetch_youtube.requests.get", return_value=fake_response(500)) as mock_get:
        with pytest.raises(RuntimeError, match="500"):
            api_get("videos", {}, api_key="fake")
    assert mock_get.call_count == 3
    assert [c.args[0] for c in mock_sleep.call_args_list] == [2, 4]
