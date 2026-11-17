-- One row per video with its engagement metrics. This is the main table for analysis.
--
-- Engagement rate = (likes + comments) / views. It is left null, not set to 0,
-- when likes or comments are hidden, so hidden stats can't drag a channel's average down.

with videos as (

    select * from {{ ref('stg_youtube__videos') }}

),

channels as (

    select * from {{ ref('stg_youtube__channels') }}

),

with_age as (

    select
        videos.*,
        date_diff('day', cast(videos.published_at_uk as date), videos.snapshot_date) as video_age_days
    from videos

)

select
    with_age.video_id,
    with_age.channel_id,
    channels.channel_title,
    channels.subscriber_count,
    with_age.title,
    with_age.published_at,
    with_age.published_at_uk,
    with_age.publish_weekday,
    with_age.publish_weekday_number,
    with_age.publish_hour,
    with_age.publish_daypart,
    with_age.video_format,
    with_age.duration_seconds,
    with_age.tags,
    with_age.view_count,
    with_age.like_count,
    with_age.comment_count,
    with_age.video_age_days,
    with_age.video_age_days >= {{ var('min_video_age_days') }} as is_mature,

    case
        when with_age.view_count > 0
            and with_age.like_count is not null
            and with_age.comment_count is not null
            then cast(with_age.like_count + with_age.comment_count as double) / with_age.view_count
    end as engagement_rate,

    case
        when with_age.view_count > 0 and with_age.like_count is not null
            then cast(with_age.like_count as double) / with_age.view_count
    end as like_rate,

    case
        when with_age.view_count > 0 and with_age.comment_count is not null
            then cast(with_age.comment_count as double) / with_age.view_count
    end as comment_rate,

    -- Views per day since upload, so older videos don't win just by being older.
    cast(with_age.view_count as double) / greatest(with_age.video_age_days, 1) as views_per_day,

    with_age.snapshot_date

from with_age
left join channels
    on with_age.channel_id = channels.channel_id
