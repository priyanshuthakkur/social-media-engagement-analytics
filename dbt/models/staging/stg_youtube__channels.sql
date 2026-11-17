-- One row per channel, with clean types.

with source as (

    select * from {{ source('youtube', 'channels') }}

)

select
    channel_id,
    channel_title,
    handle,
    country,
    subscriber_count,  -- null when the channel hides its subscriber count
    total_views,
    video_count,
    cast(snapshot_date as date) as snapshot_date
from source
