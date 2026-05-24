{{ config(
    materialized='incremental',
    unique_key='id'
) }}

with max_inserted as (
    {% if is_incremental() %}
        select max(inserted_at_local) as max_ts from {{ this }}
    {% else %}
        select null::timestamp as max_ts
    {% endif %}
),

source as (
    select s.*
    from {{ ref('stg_weather_data') }} s
    cross join max_inserted m
    {% if is_incremental() %}
        where s.inserted_at > m.max_ts
    {% endif %}
),

with_local_time as (
    select
        *,
        (time + (utc_offset || 'hours')::interval) as time_local_tz
    from source
),

de_dup as (
    select *,
        row_number() over (partition by city, time order by inserted_at desc) as rn
    from with_local_time
)

select
    id,
    city,
    temperature,
    weather_description,
    wind_speed,
    wind_gust_speed,
    humidity,
    pressure,
    visibility,
    uv_index,
    cloud_cover,
    precipitation_prob,
    dew_point,
    feels_like,
    aqi_index,
    weather_severity,
    time as weather_time_utc,
    (time + (utc_offset || 'hours')::interval) as weather_time_local,
    (inserted_at + (utc_offset || 'hours')::interval) as inserted_at_local,
    is_forecast
from de_dup
where rn = 1
order by city, time