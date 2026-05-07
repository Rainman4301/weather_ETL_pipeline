import sys
# run in container
sys.path.append('/opt/airflow/api_request')
from insert_records import *


from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.docker.operators.docker import DockerOperator
from datetime import datetime, timedelta
from docker.types import Mount




    


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
        mounts =[
            Mount(
                source='/home/rain/repo/weather_ETL_pipeline/dbt/myproject',
                target='/usr/app',
                type='bind'
            ),
            Mount(
                source='/home/rain/repo/weather_ETL_pipeline/dbt/profiles.yml',
                target='/root/.dbt/profiles.yml',
                type='bind'
            )
        ],
        network_mode='weather_etl_pipeline_my-network',
        docker_url='unix:///var/run/docker.sock',
        auto_remove='success'
    )

    task1 >> task2