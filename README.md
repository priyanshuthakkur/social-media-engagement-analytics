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
| 2. dbt models: staging, engagement metrics, data tests | ⏳ Next |
| 3. Statistical analysis | ⏳ Planned |
| 4. Streamlit dashboard + GitHub Actions CI | ⏳ Planned |

## Getting started

```bash
git clone https://github.com/priyanshuthakkur/social-media-engagement-analytics.git
cd social-media-engagement-analytics
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env              # then paste your free YouTube Data API key into .env
python run_ingest.py              # fetch + load into data/youtube.duckdb
pytest                            # tests use mock data, no API key needed
```

The channels analysed are listed in `config/channels.yml`. Change them to analyse any niche.

## Design choices

- **Raw snapshots are kept untouched** (`data/raw/<date>/`), so data can be re-processed
  without calling the API again, and repeated runs build a history of views over time.
- **Hidden stats stay missing, not zero.** Some channels hide likes; treating that as
  0 likes would wrongly drag their engagement rate down.
- **DuckDB stands in for a cloud warehouse** such as BigQuery: the same SQL and dbt models,
  with no cloud account needed.

## License

MIT. See [LICENSE](LICENSE).
