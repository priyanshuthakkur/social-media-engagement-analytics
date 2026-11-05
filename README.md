# Social Media Engagement Analytics

**Work in progress.** An end-to-end analytics engineering project on YouTube data from
UK fitness & nutrition brands. It asks the questions a social media team cares about:
**what content drives engagement, and when should we post?**

## Pipeline (planned)

```
fetch_youtube.py  ─▶  load_raw.py  ─▶  dbt models   ─▶  analysis      ─▶  dashboard
(YouTube Data API)    (DuckDB raw      (staging +       (Shorts vs        (Streamlit)
                       tables)          engagement       long-form,
                                        marts, tests)    posting time)
```

| Stage | Status |
|---|---|
| 1. Ingestion: YouTube API to raw JSON snapshots to DuckDB | ✅ Done |
| 2. dbt models: staging, engagement metrics, data tests | ✅ Done |
| 3. Statistical analysis | ⏳ Next |
| 4. Streamlit dashboard + GitHub Actions CI | ⏳ Planned |

## Getting started

Requires Python 3.10 or newer.

```bash
git clone https://github.com/priyanshuthakkur/social-media-engagement-analytics.git
cd social-media-engagement-analytics
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env              # then paste your free YouTube Data API key into .env
python run_ingest.py              # fetch + load into data/youtube.duckdb
cd dbt && dbt build && cd ..      # build the models and run the data tests
pytest                            # tests use mock data, no API key needed
```

The channels analysed are listed in `config/channels.yml`. Change them to analyse any niche.

## dbt models

| Model | What it holds |
|---|---|
| `stg_youtube__channels` | One row per channel, typed and renamed |
| `stg_youtube__videos` | One row per video, with UK posting time and a Short/long-form label |
| `fct_video_engagement` | One row per video with engagement rate, like rate, comment rate and views per day |
| `agg_engagement_by_format` | Median engagement for Shorts vs long-form, per channel |
| `agg_engagement_by_posting_time` | Median engagement by UK weekday and part of the day |

**Metric definitions**

- **Engagement rate** = (likes + comments) / views
- **Views per day** = views / days since upload, so older videos don't win just by being older
- Summaries use **medians**, so one viral video can't distort a channel's picture
- Videos under 7 days old are left out of the summaries, as their numbers are still settling

Data tests check that ids are unique and present, every video links to a channel,
format and time-of-day labels only take expected values, rates are never negative,
and likes or comments never outnumber views.

## Design choices

- **Raw snapshots are kept untouched** (`data/raw/<date>/`), so data can be re-processed
  without calling the API again, and repeated runs build a history of views over time.
- **Hidden stats stay missing, not zero.** Some channels hide likes; treating that as
  0 likes would wrongly drag their engagement rate down.
- **DuckDB stands in for a cloud warehouse** such as BigQuery: the same SQL and dbt models,
  with no cloud account needed.
- **Shorts are identified by length and upload date.** The API doesn't flag Shorts, so
  videos up to 60 seconds count as Shorts, and up to 3 minutes for uploads from
  15 Oct 2024 (when YouTube raised the limit). Live streams, which report no length, are excluded.
- **Posting time is in UK local time**, handling the switch between GMT and BST, since the
  brands' audiences are UK-based.
- **Shorts and long-form views aren't counted the same way.** Since March 2025 YouTube counts
  every play of a Short as a view, so engagement is best compared within a format.

## License

MIT. See [LICENSE](LICENSE).
