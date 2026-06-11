"""
Weather Data Transformation DAG

This DAG handles the validation and transformation of ingested weather data.
It runs every 2 hours (offset to avoid collision with ingestion) and includes
a validation task followed by dbt transformations.
"""

import sys
import os

# Add paths for local and container imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../../api_request'))
sys.path.append('/opt/airflow/api_request')

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.docker.operators.docker import DockerOperator
from datetime import datetime, timedelta
from docker.types import Mount
import docker
import psycopg2
from psycopg2 import sql


def get_host_repo_path():
    """
    Finds the host path by looking at the /opt/airflow/dags mount
    and stripping the sub-path to find the project root.
    """
    # 1. Prefer explicit env var (works on both WSL and Azure VM)
    env_path = os.environ.get('HOST_REPO_PATH')
    if env_path:
        return env_path
    
    # 2. Fall back to dynamic discovery (works on Linux/Azure VM but not WSL with user:root)
    try:
        client = docker.from_env()
        container_id = os.environ.get('HOSTNAME')
        container = client.containers.get(container_id)
        
        for mount in container.attrs['Mounts']:
            # We look for the dags mount because it's still active in your YAML
            if mount['Destination'] == '/opt/airflow/dags':
                # Example: mount['Source'] is '/home/rainuser/WeatherETL/airflow/dags'
                host_dags_path = mount['Source']
                
                # Strip '/airflow/dags' to get '/home/rainuser/WeatherETL'
                # This is the path the VM needs for the DockerOperator mounts
                root_path = host_dags_path.replace('/airflow/dags', '')
                return root_path
                
    except Exception as e:
        print(f"Dynamic path discovery failed: {e}")
        raise RuntimeError("Could not determine HOST_REPO_PATH. Set it as an env var.")
    
    raise RuntimeError("Could not determine HOST_REPO_PATH. Set it as an env var.")


def validate_raw_data():
    """
    Validate that dev.raw_weather_data has recent data (from last 75 minutes).
    Raises an exception if validation fails.
    """
    try:
        conn = psycopg2.connect(
            host=os.environ.get('DB_HOST', 'postgres'),
            database=os.environ.get('DB_NAME', 'weather_db'),
            user=os.environ.get('DB_USER', 'root'),
            password=os.environ.get('DB_PASSWORD', 'password'),
            port=os.environ.get('DB_PORT', 5432),
        )
        cursor = conn.cursor()
        
        # Check if there's data from the last 75 minutes
        cursor.execute("""
            SELECT COUNT(*) as record_count
            FROM dev.raw_weather_data
            WHERE inserted_at > NOW() - INTERVAL '75 minutes'
        """)
        
        result = cursor.fetchone()
        record_count = result[0] if result else 0
        
        cursor.close()
        conn.close()
        
        if record_count == 0:
            raise ValueError(
                "Validation failed: No recent data found in dev.raw_weather_data "
                "(last 75 minutes). Cannot proceed with transformation."
            )
        
        print(f"Validation passed: Found {record_count} recent records in dev.raw_weather_data")
        
    except Exception as e:
        print(f"Validation error: {str(e)}")
        raise


# Get the host path dynamically
HOST_REPO_PATH = get_host_repo_path()


# Default arguments for the transformation DAG
default_args = {
    'owner': 'weather_etl',
    'description': 'Weather data validation and dbt transformation',
    'start_date': datetime(2026, 5, 7, 1),  # Offset from ingestion which starts at :00
    'catchup': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=10),
    'execution_timeout': timedelta(seconds=1800),
    'sla': timedelta(seconds=2700),
}

# Create the transformation DAG
# Schedule every 2 hours at :30 minute mark to avoid collision with hourly ingestion
dag = DAG(
    dag_id='weather_data_transformation',
    default_args=default_args,
    schedule=timedelta(hours=2),
    description='Validate and transform weather data using dbt every 2 hours',
    catchup=False,
)

with dag:
    validate_data = PythonOperator(
        task_id='validate_raw_data',
        python_callable=validate_raw_data,
        doc="""
        Validate that dev.raw_weather_data has recent data from the last 75 minutes.
        This ensures data ingestion has completed successfully before transformation.
        """,
    )
    
    transform_data = DockerOperator(
        task_id='dbt_transform',
        image='ghcr.io/dbt-labs/dbt-postgres:1.9.0',
        command='run',
        working_dir='/usr/app',
        mount_tmp_dir=False,
        mounts=[
            Mount(
                source=f"{HOST_REPO_PATH}/dbt/myproject",
                target='/usr/app',
                type='bind'
            ),
            Mount(
                source=f"{HOST_REPO_PATH}/dbt/profiles.yml",
                target='/root/.dbt/profiles.yml',
                type='bind'
            )
        ],
        network_mode='weather_etl_pipeline_my-network',
        docker_url='unix:///var/run/docker.sock',
        auto_remove='success',
        doc="""
        Run dbt transformations on the validated weather data.
        This task transforms raw data in dev.raw_weather_data into
        processed data in dev.analytics_weather_data.
        """,
    )
    
    validate_data >> transform_data
