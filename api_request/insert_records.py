from api_request import *
import psycopg2
import os
import random
from datetime import datetime, timedelta

try:
    from pyspark.sql import SparkSession
    from pyspark.sql.types import (
        StructType, StructField, StringType, FloatType,
        IntegerType, TimestampType, BooleanType
    )
    from pyspark.sql import functions as F
    PYSPARK_AVAILABLE = True

    WEATHER_SCHEMA = StructType([
        StructField("city",                StringType(),   True),
        StructField("temperature",         FloatType(),    True),
        StructField("weather_description", StringType(),   True),
        StructField("wind_speed",          FloatType(),    True),
        StructField("wind_gust_speed",     FloatType(),    True),
        StructField("humidity",            FloatType(),    True),
        StructField("pressure",            FloatType(),    True),
        StructField("visibility",          FloatType(),    True),
        StructField("uv_index",            FloatType(),    True),
        StructField("cloud_cover",         FloatType(),    True),
        StructField("precipitation_prob",  FloatType(),    True),
        StructField("dew_point",           FloatType(),    True),
        StructField("feels_like",          FloatType(),    True),
        StructField("aqi_index",           FloatType(),    True),
        StructField("weather_severity",    IntegerType(),  True),
        StructField("time",                TimestampType(), True),
        StructField("utc_offset",          StringType(),   True),
        StructField("is_forecast",         BooleanType(),  True),
    ])
except ImportError:
    PYSPARK_AVAILABLE = False
    WEATHER_SCHEMA = None


from concurrent.futures import ThreadPoolExecutor, as_completed
import threading


# ─────────────────────────────────────────
# SPARK
# ─────────────────────────────────────────

def get_spark():
    return (
        SparkSession.builder
        .master("local[1]")
        .appName("WeatherETL")
        .config("spark.driver.memory", "512m")
        .config("spark.executor.memory", "512m")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )




def transform_with_spark(records, spark):
    """Apply schema, deduplicate, and validate via Spark."""
    df = spark.createDataFrame(records, schema=WEATHER_SCHEMA)

    df = (
        df.dropDuplicates(["city", "time"])
          .filter(F.col("temperature").isNotNull())
          .filter(F.col("weather_severity") >= 1)
          .orderBy("city", "time")
    )

    count = df.count()
    print(f"  Spark: {count} records after transform")
    return df.collect()


# ─────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────

def get_conn_params():
    return dict(
        host=os.getenv('DB_HOST', 'db'),
        port=int(os.getenv('DB_PORT', 5432)),
        dbname=os.getenv('DB_NAME', 'db'),
        user=os.getenv('DB_USER', 'db_user'),
        password=os.getenv('DB_PASSWORD', 'db_password'),
    )


def connect_to_db():
    print("Connecting to the database...")
    try:
        conn = psycopg2.connect(**get_conn_params())
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
    """Delete historical records older than 1 day from raw_weather_data."""
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


# ─────────────────────────────────────────
# GENERATION (parallel by city)
# ─────────────────────────────────────────

def generate_for_city(city, utc_offset, days_ahead=7, hours_historical=24):
    """Generate records for a single city — runs in its own thread."""
    weather_descriptions = [
        'Clear', 'Cloudy', 'Rainy', 'Snowy', 'Sunny', 'Foggy',
        'Windy', 'Partly Cloudy', 'Thunderstorm', 'Drizzle', 'Hail', 'Sleet'
    ]
    records = []
    now = datetime.now().replace(minute=0, second=0, microsecond=0)

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
    for interval in range(days_ahead * 24 * 2):
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

    return records


def generate_parallel(days_ahead=7, hours_historical=24, max_workers=4):
    """Fan out generation across threads, one per city."""
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
        'Singapore': '+8',
    }

    all_records = []
    lock = threading.Lock()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(generate_for_city, city, offset, days_ahead, hours_historical): city
            for city, offset in city_utc_offset.items()
        }
        for future in as_completed(futures):
            city = futures[future]
            try:
                records = future.result()
                with lock:
                    all_records.extend(records)
                print(f"  ✓ {city}: {len(records)} records generated")
            except Exception as e:
                print(f"  ✗ {city} failed: {e}")

    print(f"Total generated: {len(all_records)} records across {len(city_utc_offset)} cities")
    return all_records


# ─────────────────────────────────────────
# INSERTION (parallel by chunk)
# ─────────────────────────────────────────

def insert_chunk(conn_params, chunk, chunk_id, total):
    """Insert a single chunk — each thread gets its own connection."""
    conn = psycopg2.connect(**conn_params)
    try:
        cursor = conn.cursor()
        insert_sql = """
            INSERT INTO dev.raw_weather_data (
                city, temperature, weather_description, wind_speed, wind_gust_speed,
                humidity, pressure, visibility, uv_index, cloud_cover, precipitation_prob,
                dew_point, feels_like, aqi_index, weather_severity, time,
                inserted_at, utc_offset, is_forecast
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),%s,%s)
        """
        rows = [
            (
                r.city, r.temperature, r.weather_description, r.wind_speed,
                r.wind_gust_speed, r.humidity, r.pressure, r.visibility,
                r.uv_index, r.cloud_cover, r.precipitation_prob, r.dew_point,
                r.feels_like, r.aqi_index, r.weather_severity,
                r.time.to_pydatetime(),
                r.utc_offset, r.is_forecast
            )
            for r in chunk
        ]
        cursor.executemany(insert_sql, rows)
        conn.commit()
        print(f"  Chunk {chunk_id}/{total}: {len(rows)} rows inserted")
        cursor.close()
    except psycopg2.Error as e:
        print(f"  Chunk {chunk_id} failed: {e}")
        raise
    finally:
        conn.close()


def insert_parallel(rows, conn_params, num_threads=3, chunk_size=1000):
    """Split rows into chunks and insert each chunk in a separate thread."""
    chunks = [rows[i:i + chunk_size] for i in range(0, len(rows), chunk_size)]
    total = len(chunks)
    print(f"Inserting {len(rows)} records across {total} chunks ({num_threads} threads)...")

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [
            executor.submit(insert_chunk, conn_params, chunk, i + 1, total)
            for i, chunk in enumerate(chunks)
        ]
        for future in as_completed(futures):
            future.result()   # re-raises any exception from the thread


# ─────────────────────────────────────────
# SINGLE RECORD (API path, unchanged)
# ─────────────────────────────────────────

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


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

def main(use_random_data=True, days_ahead=7):
    conn_params = get_conn_params()

    # setup — uses a single short-lived connection
    conn = connect_to_db()
    try:
        create_table(conn)
        cleanup_old_records(conn)
    finally:
        conn.close()

    if use_random_data:
        if not PYSPARK_AVAILABLE:
            raise RuntimeError("PySpark is not installed. Run: pip install pyspark==3.5.3")
        spark = get_spark()
        try:
            print("--- Step 1: Generating records in parallel ---")
            raw_records = generate_parallel(days_ahead)

            print("--- Step 2: Transforming with Spark ---")
            clean_rows = transform_with_spark(raw_records, spark)

            print("--- Step 3: Inserting in parallel ---")
            insert_parallel(clean_rows, conn_params)
        finally:
            spark.stop()
            print("Spark session stopped.")
    else:
        conn = psycopg2.connect(**conn_params)
        try:
            data = fetch_data()
            insert_record(conn, data)
        finally:
            conn.close()
            print("Database connection closed.")


if __name__ == "__main__":
    main(use_random_data=True, days_ahead=7)