{{ config(materialized='table') }}

select
    city,
    date(weather_time_local) as date,
    round(avg(temperature)::numeric, 2) as avg_temperature,
    round(min(temperature)::numeric, 2) as min_temperature,
    round(max(temperature)::numeric, 2) as max_temperature,
    round(avg(wind_speed)::numeric, 2) as avg_wind_speed,
    round(max(wind_gust_speed)::numeric, 2) as max_wind_gust,
    round(avg(humidity)::numeric, 2) as avg_humidity,
    round(avg(pressure)::numeric, 2) as avg_pressure,
    round(avg(visibility)::numeric, 2) as avg_visibility,
    round(avg(uv_index)::numeric, 2) as avg_uv_index,
    round(avg(cloud_cover)::numeric, 2) as avg_cloud_cover,
    round(avg(precipitation_prob)::numeric, 2) as avg_precipitation_prob,
    round(avg(dew_point)::numeric, 2) as avg_dew_point,
    round(avg(feels_like)::numeric, 2) as avg_feels_like,
    round(avg(aqi_index)::numeric, 2) as avg_aqi,
    round(avg(weather_severity)::numeric, 1) as avg_weather_severity,
    max(is_forecast::int) as has_forecast_data
from {{ ref('silver_weather_data') }}
group by city, date(weather_time_local)
order by city, date(weather_time_local) desc