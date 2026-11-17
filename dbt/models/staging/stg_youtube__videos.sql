-- One row per video, with clean types, a Short/long-form label and UK posting time.

with source as (

    select * from {{ source('youtube', 'videos') }}

),

cleaned as (

    select
        video_id,
        channel_id,
        title,
        published_at,
        -- The audience is UK-based, so posting time is analysed in UK local time
        -- (this also handles the switch between GMT and BST).
        timezone('Europe/London', published_at) as published_at_uk,
        -- Live streams and premieres report a duration of 0, which isn't a real length.
        nullif(duration_seconds, 0) as duration_seconds,
        view_count,
        like_count,       -- null when likes are hidden
        comment_count,    -- null when comments are turned off
        nullif(tags, '') as tags,
        cast(snapshot_date as date) as snapshot_date
    from source

)

select
    *,

    case
        when duration_seconds is null then null
        when duration_seconds <= {{ var('shorts_max_seconds_legacy') }} then 'short'
        when duration_seconds <= {{ var('shorts_max_seconds') }}
            and published_at_uk >= cast('{{ var("shorts_3min_start_date") }}' as timestamp)
            then 'short'
        else 'long_form'
    end as video_format,

    dayname(published_at_uk) as publish_weekday,
    isodow(published_at_uk) as publish_weekday_number,  -- 1 = Monday, for sorting
    hour(published_at_uk) as publish_hour,

    case
        when hour(published_at_uk) between 6 and 11 then 'morning (06-12)'
        when hour(published_at_uk) between 12 and 16 then 'afternoon (12-17)'
        when hour(published_at_uk) between 17 and 21 then 'evening (17-22)'
        else 'night (22-06)'
    end as publish_daypart

from cleaned
