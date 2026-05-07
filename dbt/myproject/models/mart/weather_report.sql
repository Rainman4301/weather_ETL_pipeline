{{
    config(
        materialized='table',
        unique_key='id',
        schema='analytics'
    )
}}

select
    id,
    city,
    temperature,
    weather_description,
    wind_speed,
    humidity,
    pressure,
    weather_time_local,
    weather_time_utc,
    is_forecast
from
{{ ref('stg_weather_data') }}
order by city, weather_time_local desc