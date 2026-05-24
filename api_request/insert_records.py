from api_request import *
import psycopg2
import os
import random
from datetime import datetime, timedelta


def connect_to_db():
    print("Connecting to the database...")

    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'db'),
            port=int(os.getenv('DB_PORT', 5432)),
            dbname=os.getenv('DB_NAME', 'db'),
            user=os.getenv('DB_USER', 'db_user'),
            password=os.getenv('DB_PASSWORD', 'db_password')
        )
        return conn
    except psycopg2.Error as e:
        print("Error connecting to the database:", e)
        raise


def create_table(conn):
    print("Creating the weather_data table if it doesn't exist...")

    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE SCHEMA IF NOT EXISTS dev;

            CREATE TABLE IF NOT EXISTS dev.raw_weather_data (
                id SERIAL PRIMARY KEY,
                city TEXT,
                temperature FLOAT,
                weather_description TEXT,
                wind_speed FLOAT,
                wind_gust_speed FLOAT,
                humidity FLOAT,
                pressure FLOAT,
                visibility FLOAT,
                uv_index FLOAT,
                cloud_cover FLOAT,
                precipitation_prob FLOAT,
                dew_point FLOAT,
                feels_like FLOAT,
                aqi_index FLOAT,
                weather_severity INT,
                time TIMESTAMP,
                inserted_at TIMESTAMP DEFAULT NOW(),
                utc_offset TEXT,
                is_forecast BOOLEAN DEFAULT TRUE
            );
        """)
        conn.commit()
        print("Table created successfully.")
        cursor.close()

    except psycopg2.Error as e:
        print("Error creating the table:", e)
        raise


def cleanup_old_records(conn):
    """
    Delete historical records older than 1 day from raw_weather_data.
    Forecast data is kept regardless of age.
    """
    print("Cleaning up old historical records...")

    try:
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM dev.raw_weather_data
            WHERE is_forecast = FALSE
            AND time < NOW() - INTERVAL '1 day'
        """)
        deleted = cursor.rowcount
        conn.commit()
        print(f"Deleted {deleted} old historical records.")
        cursor.close()

    except psycopg2.Error as e:
        print("Error cleaning up old records:", e)
        raise


def generate_random_weather_data(days_ahead=7, hours_historical=24):
    """
    Generate future weather forecast data at 30-minute intervals and keep historical data.

    Args:
        days_ahead (int): Number of days ahead to generate forecast for (default: 7)
        hours_historical (int): Hours of historical data to keep (default: 24 = 1 day)

    Returns:
        list: List of tuples containing weather forecast data
    """
    print(f"Generating weather records: {hours_historical}h historical + {days_ahead} days forecast at 30-min intervals...")

    city_utc_offset = {
        'London': '+0',
        'New York': '-5',
        'Tokyo': '+9',
        'Paris': '+1',
        'Sydney': '+10',
        'Berlin': '+1',
        'Toronto': '-5',
        'Mumbai': '+5:30',
        'Dubai': '+4',
        'Singapore': '+8'
    }

    weather_descriptions = ['Clear', 'Cloudy', 'Rainy', 'Snowy', 'Sunny', 'Foggy',
                            'Windy', 'Partly Cloudy', 'Thunderstorm', 'Drizzle', 'Hail', 'Sleet']

    records = []
    now = datetime.now().replace(minute=0, second=0, microsecond=0)

    for city, utc_offset in city_utc_offset.items():
        # Historical data
        for hours_back in range(hours_historical * 2):
            historical_time = now - timedelta(minutes=30 * hours_back)
            base_temp = 15 + 10 * ((hours_back % 24) - 12) / 12
            temperature = round(base_temp + random.uniform(-3, 3), 1)
            humidity = round(max(30, 90 - abs((hours_back % 24) - 12) * 3 + random.uniform(-10, 10)), 1)
            wind_speed = round(random.uniform(0, 15), 1)
            wind_gust = round(wind_speed + random.uniform(2, 8), 1)
            pressure = round(1013 + random.uniform(-5, 5), 2)
            visibility = round(random.uniform(5, 15), 1)
            uv_index = round(max(0, 6 * ((12 - abs((hours_back % 24) - 12)) / 12)) + random.uniform(-0.5, 0.5), 1)
            cloud_cover = round(random.uniform(10, 90), 1)
            precipitation_prob = round(random.uniform(0, 60), 1)
            dew_point = round(temperature - ((100 - humidity) / 5), 1)
            feels_like = round(temperature - (wind_speed * 0.2) - ((100 - humidity) / 10), 1)
            aqi = round(random.uniform(0, 150), 1)
            severity = max(1, int((precipitation_prob / 20) + (wind_speed / 5) + (abs(temperature - 15) / 5)))

            records.append((
                city, temperature, random.choice(weather_descriptions), wind_speed, wind_gust,
                humidity, pressure, visibility, uv_index, cloud_cover, precipitation_prob,
                dew_point, feels_like, aqi, severity, historical_time, utc_offset, False
            ))

        # Forecast data
        total_intervals = days_ahead * 24 * 2
        for interval in range(total_intervals):
            forecast_time = now + timedelta(minutes=30 * interval)
            hour_of_day = (interval // 2) % 24
            base_temp = 15 + 10 * ((hour_of_day - 12) / 12)
            temperature = round(base_temp + random.uniform(-5, 5), 1)
            humidity = round(max(30, 90 - abs(hour_of_day - 12) * 3 + random.uniform(-15, 15)), 1)
            wind_speed = round(random.uniform(0, 20), 1)
            wind_gust = round(wind_speed + random.uniform(3, 10), 1)
            pressure = round(1013 + random.uniform(-8, 8), 2)
            visibility = round(max(1, 15 - (cloud_cover / 10)) if (cloud_cover := random.uniform(10, 100)) else 15, 1)
            cloud_cover = round(random.uniform(0, 100), 1)
            uv_index = round(max(0, 6 * ((12 - abs(hour_of_day - 12)) / 12)) + random.uniform(-1, 1), 1)
            precipitation_prob = round(random.uniform(0, 80), 1)
            dew_point = round(temperature - ((100 - humidity) / 5), 1)
            feels_like = round(temperature - (wind_speed * 0.2) - ((100 - humidity) / 10), 1)
            aqi = round(random.uniform(0, 200), 1)
            severity = max(1, int((precipitation_prob / 20) + (wind_speed / 5) + (abs(temperature - 15) / 5)))

            records.append((
                city, temperature, random.choice(weather_descriptions), wind_speed, wind_gust,
                humidity, pressure, visibility, uv_index, cloud_cover, precipitation_prob,
                dew_point, feels_like, aqi, severity, forecast_time, utc_offset, True
            ))

    total_records = len(records)
    print(f"Generated {total_records} records ({len(city_utc_offset)} cities × ({hours_historical}h hist + {days_ahead}d forecast) at 30-min intervals)")
    return records


def insert_batch_records(conn, records, chunk_size=1000):
    """
    Insert weather records in chunks to avoid loading everything into memory.

    Args:
        conn: Database connection
        records (list): List of tuples containing weather data
        chunk_size (int): Number of records per chunk (default: 1000)
    """
    print(f"Inserting {len(records)} records in chunks of {chunk_size}...")

    insert_sql = """
        INSERT INTO dev.raw_weather_data (
            city, temperature, weather_description, wind_speed, wind_gust_speed,
            humidity, pressure, visibility, uv_index, cloud_cover, precipitation_prob,
            dew_point, feels_like, aqi_index, weather_severity, time,
            inserted_at, utc_offset, is_forecast
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s, %s)
    """

    try:
        cursor = conn.cursor()
        total_chunks = (len(records) // chunk_size) + 1

        for i in range(0, len(records), chunk_size):
            chunk = records[i:i + chunk_size]
            cursor.executemany(insert_sql, chunk)
            conn.commit()
            print(f"  Chunk {i // chunk_size + 1}/{total_chunks} inserted ({len(chunk)} records)")

        print(f"{len(records)} records inserted successfully.")
        cursor.close()

    except psycopg2.Error as e:
        print("Error inserting records:", e)
        raise


def insert_record(conn, data):
    print("Inserting a single record into the database...")

    try:
        weather = data['current']
        location = data['location']

        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO dev.raw_weather_data (
                city, temperature, weather_description, wind_speed,
                humidity, pressure, time, inserted_at, utc_offset, is_forecast
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s, FALSE)
            """,
            (
                location['name'],
                weather['temperature'],
                weather['weather_descriptions'][0] if weather['weather_descriptions'] else None,
                weather['wind_speed'],
                weather.get('humidity', 0),
                weather.get('pressure', 0),
                location['localtime'],
                location['utc_offset']
            )
        )
        conn.commit()
        print("Record inserted successfully.")
        cursor.close()

    except psycopg2.Error as e:
        print("Error inserting the record:", e)
        raise


def main(use_random_data=True, days_ahead=7):
    """
    Main function to insert weather data.

    Args:
        use_random_data (bool): If True, generates forecast data; if False, fetches from API
        days_ahead (int): Number of days ahead for forecast data (default: 7)
    """
    try:
        conn = connect_to_db()
        create_table(conn)
        cleanup_old_records(conn)      # ← delete old historical data first

        if use_random_data:
            records = generate_random_weather_data(days_ahead)
            insert_batch_records(conn, records)
        else:
            data = fetch_data()
            insert_record(conn, data)

    except Exception as e:
        print("An error occurred:", e)

    finally:
        if 'conn' in locals() and conn:
            conn.close()
            print("Database connection closed.")


if __name__ == "__main__":
    main(use_random_data=True, days_ahead=7)