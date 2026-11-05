-- Rates can never be negative, and likes or comments outnumbering views would
-- point to a data problem. Any rows returned here fail the test.

select
    video_id,
    engagement_rate,
    like_rate,
    comment_rate
from {{ ref('fct_video_engagement') }}
where engagement_rate < 0
    or like_rate < 0
    or comment_rate < 0
    or like_rate > 1
    or comment_rate > 1
