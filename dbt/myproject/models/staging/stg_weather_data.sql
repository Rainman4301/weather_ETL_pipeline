{{ config(
    materialized='incremental',
    unique_key='id',
    post_hook="DELETE FROM {{ this }} WHERE inserted_at < NOW() - INTERVAL '30 days'",
    contract={"enforced": true}
) }}

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
    time,
    inserted_at,
    utc_offset,
    is_forecast
from {{ source('dev', 'raw_weather_data') }}

{% if is_incremental() %}
    where inserted_at > (select max(inserted_at) from {{ this }})
{% endif %}