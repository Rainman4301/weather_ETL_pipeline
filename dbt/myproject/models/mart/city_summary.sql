-- latest reading per city
select distinct on (city)
    city, temperature, weather_description,
    wind_speed, humidity, pressure,
    weather_time_local, is_forecast
from {{ ref('silver_weather_data') }}
order by city, weather_time_local desc