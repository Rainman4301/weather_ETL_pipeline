import requests
import os





# Get configuration from environment variables
API_KEY = os.getenv('WEATHER_API_KEY')
API_BASE_URL = os.getenv('WEATHER_API_BASE_URL')
CITY = os.getenv('WEATHER_API_CITY')



def fetch_data(city=None):

    # Validate configuration
    if not API_KEY:
        raise ValueError("WEATHER_API_KEY environment variable is not set!")
    if not API_BASE_URL:
        raise ValueError("WEATHER_API_BASE_URL environment variable is not set!")

    api_url = f"{API_BASE_URL}?access_key={API_KEY}&query={CITY}"

    """
    Fetch weather data from weatherstack API
    
    Args:
        city (str): City name to fetch weather for. Uses WEATHER_API_CITY env var if not provided.
    
    Returns:
        dict: Weather data JSON response
    """
    # Use provided city or fallback to environment variable
    target_city = city or CITY
    
    # Build URL dynamically
    request_url = f"{API_BASE_URL}?access_key={API_KEY}&query={target_city}"

    print(f"Fetching weather data for {target_city}...")
    try:
        response = requests.get(request_url)
        response.raise_for_status()  # Check if the request was successful
        print("Data fetched successfully!")
        return response.json()  # Return the JSON data

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        raise
    except Exception as err:
        print(f"Error fetching data: {err}")
        raise

    

# fetch_data()

def mock_fetch_data():
    print("Mock fetching data...")
    return {'request': {'type': 'City', 'query': 'New York, United States of America', 'language': 'en', 'unit': 'm'}, 'location': {'name': 'New York', 'country': 'United States of America', 'region': 'New York', 'lat': '40.714', 'lon': '-74.006', 'timezone_id': 'America/New_York', 'localtime': '2026-04-03 09:14', 'localtime_epoch': 1775207640, 'utc_offset': '-4.0'}, 'current': {'observation_time': '01:14 PM', 'temperature': 6, 'weather_code': 143, 'weather_icons': ['https://cdn.worldweatheronline.com/images/wsymbols01_png_64/wsymbol_0006_mist.png'], 'weather_descriptions': ['Mist'], 'astro': {'sunrise': '06:36 AM', 'sunset': '07:23 PM', 'moonrise': '09:24 PM', 'moonset': '06:58 AM', 'moon_phase': 'Waning Gibbous', 'moon_illumination': 99}, 'air_quality': {'co': '262.85', 'no2': '25.05', 'o3': '61', 'so2': '7.35', 'pm2_5': '16.45', 'pm10': '18.95', 'us-epa-index': '2', 'gb-defra-index': '2'}, 'wind_speed': 9, 'wind_degree': 156, 'wind_dir': 'SSE', 'pressure': 1028, 'precip': 0, 'humidity': 96, 'cloudcover': 100, 'feelslike': 4, 'uv_index': 1, 'visibility': 3, 'is_day': 'yes'}}
    