-- Shorts vs long-form, per channel.
--
-- Medians are used rather than averages because a single viral video would
-- otherwise dominate. Only videos old enough for their numbers to settle are used.
--
-- Note: since March 2025 YouTube counts every play of a Short (including replays)
-- as a view, so Shorts views run higher than long-form views. Compare engagement
-- rates within a format across channels, or treat cross-format gaps with care.

select
    channel_id,
    channel_title,
    video_format,
    count(*) as video_count,
    count(engagement_rate) as videos_with_engagement_data,
    median(engagement_rate) as median_engagement_rate,
    median(like_rate) as median_like_rate,
    median(comment_rate) as median_comment_rate,
    median(views_per_day) as median_views_per_day,
    median(view_count) as median_views
from {{ ref('fct_video_engagement') }}
where is_mature
    and video_format is not null
group by channel_id, channel_title, video_format
