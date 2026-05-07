{{ config(
    materialized='table',
    unique_key='id',
    schema='analytics'
)}}

with source as (
    select 
        id,
        city,
        temperature,
        weather_description,
        wind_speed,
        humidity,
        pressure,
        time,
        inserted_at,
        utc_offset,
        is_forecast
    from
        {{ source('dev', 'raw_weather_data') }}
),

-- Convert time to city's local timezone for filtering
with_local_time as (
    select 
        *,
        -- Adjust time to city's local timezone
        (time + (utc_offset || 'hours')::interval) as time_local_tz
    from source
),

-- Keep only forecast data or recent historical data (within last 12 hours from the record's local time)
filtered_data as (
    select 
        *
    from with_local_time
    where 
        is_forecast = TRUE
        or (is_forecast = FALSE and time_local_tz > (now() AT TIME ZONE 'UTC' - interval '12 hours'))
),

-- Deduplicate: keep the most recent insertion for each time slot per city
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
    humidity,
    pressure,
    time as weather_time_utc,
    (time + (utc_offset || 'hours')::interval) as weather_time_local,
    (inserted_at + (utc_offset || 'hours')::interval) as inserted_at_local,
    is_forecast
from de_dup
where rn = 1
order by city, time
