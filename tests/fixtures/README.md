# Sample data

`sample_snapshot/` holds a small, **made-up** YouTube API snapshot (two fictional
channels, twelve videos). It is shaped exactly like a real snapshot in `data/raw/`
and deliberately includes the awkward cases the models must handle:

- a video with likes hidden (missing, not zero)
- a live stream (`P0D` duration) and an upcoming premiere with no stats yet
- Shorts (up to 3 minutes) alongside long-form videos

It lets anyone, including CI, build and test the dbt models without an API key:

```bash
python scripts/build_sample_db.py
cd dbt && dbt build && cd ..
```
