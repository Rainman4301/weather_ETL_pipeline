"""
Weather Data Ingestion DAG

This DAG handles the ingestion of weather data from external APIs.
It runs every hour and calls the main() function from insert_records.py.
"""

import sys
import os

# Add paths for local and container imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../../api_request'))
sys.path.append('/opt/airflow/api_request')

from insert_records import main
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import docker


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


# Get the host path dynamically
HOST_REPO_PATH = get_host_repo_path()


# Default arguments for the ingestion DAG
default_args = {
    'owner': 'weather_etl',
    'description': 'Weather data ingestion from external APIs',
    'start_date': datetime(2026, 5, 7),
    'catchup': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(seconds=600),
    'sla': timedelta(seconds=900),
}

# Create the ingestion DAG
dag = DAG(
    dag_id='weather_data_ingestion',
    default_args=default_args,
    schedule=timedelta(hours=1),
    description='Ingest weather forecast data from external APIs every hour',
    catchup=False,
)

with dag:
    ingest_data = PythonOperator(
        task_id='ingest_data',
        python_callable=main,
        doc="""
        Call the main() function from insert_records.py to fetch
        weather data from external APIs and insert into the database.
        """,
    )
