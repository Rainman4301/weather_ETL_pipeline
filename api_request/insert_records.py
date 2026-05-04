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
                time TIMESTAMP,
                inserted_at TIMESTAMP DEFAULT NOW(),
                utc_offset TEXT
            );

            """)


        conn.commit()
        print("Table created successfully.")


        cursor.close()


    except psycopg2.Error as e:
        print("Error creating the table:", e)
        raise

    




def generate_random_weather_data(num_records=2000, days_back=14):
    """
    Generate random weather data for the past N days.
    
    Args:
        num_records (int): Number of random records to generate (default: 2000)
        days_back (int): Number of days back to generate data for (default: 14)
    
    Returns:
        list: List of tuples containing weather data
    """
    print(f"Generating {num_records} random weather records from the past {days_back} days...")
    
    cities = ['London', 'New York', 'Tokyo', 'Paris', 'Sydney', 'Berlin', 'Toronto', 'Mumbai', 'Dubai', 'Singapore']
    weather_descriptions = ['Clear', 'Cloudy', 'Rainy', 'Snowy', 'Sunny', 'Foggy', 'Windy', 'Partly Cloudy', 'Thunderstorm', 'Drizzle']
    utc_offsets = ['-5', '-6', '+9', '+1', '+10', '+1', '-5', '+5:30', '+4', '+8']
    
    records = []
    now = datetime.now()
    
    for _ in range(num_records):
        # Random timestamp within the past N days
        days_ago = random.randint(0, days_back - 1)
        hours_ago = random.randint(0, 23)
        minutes_ago = random.randint(0, 59)
        
        timestamp = now - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
        
        city = random.choice(cities)
        temperature = round(random.uniform(-10, 40), 1)
        weather_description = random.choice(weather_descriptions)
        wind_speed = round(random.uniform(0, 30), 1)
        utc_offset = random.choice(utc_offsets)
        
        records.append((
            city,
            temperature,
            weather_description,
            wind_speed,
            timestamp,
            utc_offset
        ))
    
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
                time, 
                inserted_at,
                utc_offset
            )
            VALUES (%s, %s, %s, %s, %s, NOW(), %s)
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
            time, 
            inserted_at,
            utc_offset
            )
            VALUES (%s, %s, %s, %s, %s, NOW(), %s)
        """,
        
        (
            location['name'],
            weather['temperature'],
            weather['weather_descriptions'][0] if weather['weather_descriptions'] else None,
            weather['wind_speed'],
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



def main(use_random_data=True, num_records=2000, days_back=14):
    """
    Main function to insert weather data.
    
    Args:
        use_random_data (bool): If True, generates random data; if False, fetches from API (default: True)
        num_records (int): Number of random records to generate (default: 2000)
        days_back (int): Number of days back for random data (default: 14)
    """
    try:
        conn = connect_to_db()
        create_table(conn)
        
        if use_random_data:
            # Generate and insert 2000 random records
            records = generate_random_weather_data(num_records, days_back)
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
    # By default, insert 2000 random records from the past 2 weeks
    main(use_random_data=True, num_records=2000, days_back=14)
    

 
