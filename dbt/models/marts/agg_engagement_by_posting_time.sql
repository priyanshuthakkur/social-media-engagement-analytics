-- Engagement by UK posting day and time of day, split by format.
--
-- Times are grouped into four parts of the day rather than single hours, because
-- a few hundred videos per channel spread over 168 weekly hours would leave most
-- slots with too few videos to say anything. video_count shows how much evidence
-- sits behind each median, so thin slots can be ignored in the analysis.

select
    video_format,
    publish_weekday,
    publish_weekday_number,
    publish_daypart,
    count(*) as video_count,
    count(distinct channel_id) as channel_count,
    median(engagement_rate) as median_engagement_rate,
    median(views_per_day) as median_views_per_day
from {{ ref('fct_video_engagement') }}
where is_mature
    and video_format is not null
group by video_format, publish_weekday, publish_weekday_number, publish_daypart
