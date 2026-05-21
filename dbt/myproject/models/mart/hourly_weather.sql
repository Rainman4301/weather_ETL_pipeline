{{ config(materialized='table') }}

select
    id, city, temperature, weather_description,
    wind_speed, wind_gust_speed, humidity, pressure,
    visibility, uv_index, cloud_cover, precipitation_prob,
    dew_point, feels_like, aqi_index, weather_severity,
    weather_time_local, weather_time_utc, is_forecast
from {{ ref('silver_weather_data') }}
order by city, weather_time_local desc