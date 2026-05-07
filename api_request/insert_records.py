from api_request import *
import psycopg2
import random
from datetime import datetime, timedelta

# print(mock_fetch_data())


def connect_to_db():
    print("Connecting to the database...")

    try:
        conn = psycopg2.connect(
            host="db",
            port=5432,
            dbname="db",
            user="db_user",
            password="db_password"
        )
        # print(conn)

        return conn
    except psycopg2.Error as e:
        print("Error connecting to the database:", e)
        raise


def create_table(conn):
    print("Creating the weather_data table if it doesn't exist...")

    try:
        cursor = conn.cursor()
        
        cursor.execute( """

            CREATE SCHEMA IF NOT EXISTS dev;

            CREATE TABLE IF NOT EXISTS dev.raw_weather_data (
                id SERIAL PRIMARY KEY,
                city TEXT,
                temperature FLOAT,
                weather_description TEXT,
                wind_speed FLOAT,
                humidity FLOAT,
                pressure FLOAT,
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

    




def generate_random_weather_data(days_ahead=7):
    """
    Generate future weather forecast data for the next N days.
    Creates one hourly entry per city at the top of each hour (00 minutes, 00 seconds).
    
    Args:
        days_ahead (int): Number of days ahead to generate forecast for (default: 7)
    
    Returns:
        list: List of tuples containing weather forecast data
    """
    print(f"Generating future weather forecast records for the next {days_ahead} days...")
    
    # City to UTC offset mapping (using winter time for consistency)
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
    now = datetime.now().replace(minute=0, second=0, microsecond=0)  # Start at top of hour
    
    # Generate hourly forecast for each city for the next N days
    for city, utc_offset in city_utc_offset.items():
        # Generate 24 hours * days_ahead entries per city
        for day in range(days_ahead):
            for hour in range(24):
                # Calculate forecast timestamp
                forecast_time = now + timedelta(days=day, hours=hour)
                
                # Generate realistic weather data with some correlation
                temperature = round(random.uniform(-5, 35), 1)
                humidity = round(random.uniform(30, 95), 1)
                pressure = round(random.uniform(1000, 1025), 2)
                wind_speed = round(random.uniform(0, 25), 1)
                weather_description = random.choice(weather_descriptions)
                
                records.append((
                    city,
                    temperature,
                    weather_description,
                    wind_speed,
                    humidity,
                    pressure,
                    forecast_time,
                    utc_offset
                ))
    
    print(f"Generated {len(records)} forecast records ({len(city_utc_offset)} cities × 24 hours × {days_ahead} days)")
    return records


def insert_batch_records(conn, records):
    """
    Insert multiple weather records into the database.
    
    Args:
        conn: Database connection
        records (list): List of tuples containing weather data
    """
    print(f"Inserting {len(records)} records into the database...")
    
    try:
        cursor = conn.cursor()
        
        # Insert all records in a batch
        cursor.executemany(
            """
            INSERT INTO dev.raw_weather_data (
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
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s, TRUE)
            """,
            records
        )
        
        conn.commit()
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
        use_random_data (bool): If True, generates future forecast data; if False, fetches from API (default: True)
        days_ahead (int): Number of days ahead for forecast data (default: 7)
    """
    try:
        conn = connect_to_db()
        create_table(conn)
        
        if use_random_data:
            # Generate and insert forecast data for the next 7 days
            records = generate_random_weather_data(days_ahead)
            insert_batch_records(conn, records)
        else:
            # Fetch from API and insert single record
            data = fetch_data()
            insert_record(conn, data)
            
    except Exception as e:
        print("An error occurred:", e)

    finally:
        if 'conn' in locals() and conn:
            conn.close()
            print("Database connection closed.")


if __name__ == "__main__":
    # By default, insert 7 days of future forecast data
    main(use_random_data=True, days_ahead=7)
    

 
