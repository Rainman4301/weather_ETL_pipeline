{{ config(
    materialized='ephemeral'
) }}

-- Validation query for raw_weather_data quality checks
-- Can be used by Airflow before running dbt to ensure data quality
-- Run this query to identify records with data quality issues
-- Note: This is ephemeral, so it won't create a table in the database

select
    'raw_weather_data' as table_name,
    count(*) as total_records,
    sum(case when id is null then 1 else 0 end) as null_id_count,
    sum(case when city is null then 1 else 0 end) as null_city_count,
    sum(case when temperature is null then 1 else 0 end) as null_temperature_count,
    sum(case when weather_severity is null then 1 else 0 end) as null_weather_severity_count,
    sum(case when time is null then 1 else 0 end) as null_time_count,
    sum(case when temperature < -60 or temperature > 60 then 1 else 0 end) as invalid_temperature_count,
    sum(case when weather_severity < 0 or weather_severity > 10 then 1 else 0 end) as invalid_severity_count,
    sum(case when humidity < 0 or humidity > 100 then 1 else 0 end) as invalid_humidity_count,
    sum(case when pressure < 870 or pressure > 1085 then 1 else 0 end) as invalid_pressure_count,
    sum(case when cloud_cover < 0 or cloud_cover > 100 then 1 else 0 end) as invalid_cloud_cover_count,
    sum(case when precipitation_prob < 0 or precipitation_prob > 100 then 1 else 0 end) as invalid_precipitation_prob_count,
    sum(case when is_forecast is null then 1 else 0 end) as null_is_forecast_count,
    max(inserted_at) as latest_inserted_at,
    current_timestamp - max(inserted_at) as data_age,
    case
        when current_timestamp - max(inserted_at) > interval '120 minutes' then 'ERROR: Data is stale (older than 120 minutes)'
        when current_timestamp - max(inserted_at) > interval '90 minutes' then 'WARN: Data may be stale (older than 90 minutes)'
        else 'OK: Data is fresh'
    end as freshness_status
from {{ source('dev', 'raw_weather_data') }}
group by table_name
