import sys
# run in container
sys.path.append('/opt/airflow/api_request')
from insert_records import *


from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.docker.operators.docker import DockerOperator
from datetime import datetime, timedelta
from docker.types import Mount


import os
import docker
def get_host_repo_path():
    """
    Finds the host path by looking at the /opt/airflow/dags mount
    and stripping the sub-path to find the project root.
    """
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
        return '/opt/airflow' # Last resort fallback
    return '/opt/airflow'

# Get the host path dynamically
HOST_REPO_PATH = get_host_repo_path()

    


default_args = {
    'description': 'A DAG to orchestrate the weather ETL pipeline',
    'start_date': datetime(2026, 5, 7),
    'catchup': False,
}


dag = DAG(
    dag_id='weather_api_dbt_orchestrator',
    default_args=default_args,
    schedule=timedelta(hours=1),
    description='Hourly weather forecast ETL pipeline'
)

with dag:
    task1 = PythonOperator(
        task_id='ingest_data_task',
        python_callable=main
    )
    task2 = DockerOperator(
        task_id='transform_data_task',
        image='ghcr.io/dbt-labs/dbt-postgres:1.9.latest',
        command='run',
        working_dir='/usr/app',
        # FIX 1: Disable temporary directory mounting
        mount_tmp_dir=False,
        mounts =[
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
        auto_remove='success'
    )

    task1 >> task2