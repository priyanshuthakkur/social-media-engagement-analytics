"""
Checks the dbt models' outputs on the made-up sample snapshot.

These run after the warehouse has been built, so they are skipped otherwise:

    python scripts/build_sample_db.py
    cd dbt && dbt build && cd ..
    pytest
"""
import os

import pytest

duckdb = pytest.importorskip("duckdb")

DB_PATH = "data/youtube.duckdb"


@pytest.fixture(scope="module")
def con():
    if not os.path.exists(DB_PATH):
        pytest.skip("Warehouse not built yet (run the sample build and dbt first)")
    connection = duckdb.connect(DB_PATH, read_only=True)
    try:
        connection.execute("select 1 from marts.fct_video_engagement limit 1")
    except duckdb.Error:
        connection.close()
        pytest.skip("dbt models not built yet")
    yield connection
    connection.close()


def video(con, video_id, columns):
    return con.execute(
        f"select {columns} from marts.fct_video_engagement where video_id = ?", [video_id]
    ).fetchone()


def test_live_streams_and_premieres_have_no_format(con):
    # Zero-length live streams and premieres can't be labelled Short or long-form
    assert video(con, "v05", "video_format") == (None,)
    assert video(con, "v06", "video_format") == (None,)


def test_hidden_likes_give_missing_engagement_not_zero(con):
    rate, like_rate, comment_rate = video(con, "v04", "engagement_rate, like_rate, comment_rate")
    assert rate is None and like_rate is None
    assert comment_rate == pytest.approx(35 / 9800)


def test_engagement_rate_formula(con):
    # v01: (610 likes + 48 comments) / 15,400 views
    (rate,) = video(con, "v01", "engagement_rate")
    assert rate == pytest.approx((610 + 48) / 15400)


def test_shorts_flag_uses_length_and_upload_date(con):
    assert video(con, "v02", "video_format") == ("short",)      # 32 seconds
    assert video(con, "v03", "video_format") == ("short",)      # 2m45s, after Oct 2024
    assert video(con, "v01", "video_format") == ("long_form",)  # 12m40s


def test_posting_time_converted_to_uk_time_including_bst(con):
    # v01 published 17:30 UTC on 3 Oct 2026, during British Summer Time -> 18:30 UK
    hour, weekday, daypart = video(con, "v01", "publish_hour, publish_weekday, publish_daypart")
    assert (hour, weekday, daypart) == (18, "Saturday", "evening (17-22)")
    # v11 published 10:00 UTC on 25 Oct 2026, the day the clocks go back -> 10:00 UK (GMT)
    assert video(con, "v11", "publish_hour") == (10,)


def test_new_videos_are_left_out_of_summaries(con):
    # v12 is 3 days old at the snapshot, below the 7-day threshold
    assert video(con, "v12", "is_mature") == (False,)
    assert video(con, "v11", "is_mature") == (True,)


def test_format_summary_covers_mature_videos_only(con):
    rows = con.execute(
        "select channel_title, video_format, video_count from marts.agg_engagement_by_format"
    ).fetchall()
    # 12 videos - 2 without a format (live stream, premiere) - 1 too new = 9
    assert sum(r[2] for r in rows) == 9
    assert {(r[0], r[1]) for r in rows} == {
        ("Sample Fitness Co", "short"),
        ("Sample Fitness Co", "long_form"),
        ("Sample Nutrition Ltd", "short"),
        ("Sample Nutrition Ltd", "long_form"),
    }
