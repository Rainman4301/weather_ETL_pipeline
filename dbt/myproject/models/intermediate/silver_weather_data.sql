{{ config(
    materialized='table',
    unique_key='id'
) }}

with source as (
    select * from {{ ref('stg_weather_data') }}
),

with_local_time as (
    select
        *,
        (time + (utc_offset || 'hours')::interval) as time_local_tz
    from source
),

filtered_data as (
    select *
    from with_local_time
    where
        is_forecast = TRUE
        or (is_forecast = FALSE and time_local_tz > (now() AT TIME ZONE 'UTC' - interval '1 day'))
),

de_dup as (
    select *,
        row_number() over (partition by city, time order by inserted_at desc) as rn
    from filtered_data
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