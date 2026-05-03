# Weather ETL Pipeline

A comprehensive Extract, Transform, and Load (ETL) pipeline for weather data collection, storage, and analysis. This project orchestrates weather data ingestion from the WeatherStack API, loads it into PostgreSQL, and transforms it using dbt for analytical insights.

## Project Overview

This ETL pipeline automates the process of:
- **Extracting** weather data from the WeatherStack API
- **Loading** raw data into a PostgreSQL database
- **Transforming** data using dbt for analytics-ready datasets
- **Orchestrating** the entire workflow with Apache Airflow
- **Visualizing** results with Superset (optional)

### Key Components

```
weather_ETL_pipeline/
├── airflow/              # Airflow DAG orchestration
├── api_request/          # Weather API data extraction modules
├── dbt/                  # Data transformation models
├── docker/               # Docker configuration and initialization scripts
├── postgres/             # PostgreSQL database initialization
└── docker-compose.yaml   # Complete infrastructure setup
```

## Technology Stack

- **Apache Airflow 3.0.0** - Workflow orchestration and scheduling
- **PostgreSQL 14.17** - Data warehouse
- **dbt (Data Build Tool)** - SQL-based data transformation
- **Python** - API integration and data processing
- **Docker & Docker Compose** - Containerization and orchestration
- **Superset** (Optional) - Data visualization and dashboarding

## Architecture

```
┌──────────────────────┐
│   WeatherStack API   │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────────────────────────┐
│   Airflow (Orchestration Layer)          │
│  - Data Ingestion Task (Python)          │
│  - Data Transformation Task (Docker)     │
└──────────┬─────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────┐
│   PostgreSQL Database                    │
│  - Raw data schema (api_data)            │
│  - dbt transformed schemas (staging, mart)
└──────────┬─────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────┐
│   Analytics & Visualization              │
│  - dbt Models (staging, mart)            │
│  - Superset Dashboards (optional)        │
└──────────────────────────────────────────┘
```

## Prerequisites

- Docker and Docker Compose (v3.0+)
- Git
- WeatherStack API key (free tier available at [weatherstack.com](https://weatherstack.com))
- At least 4GB of available disk space

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd weather_ETL_pipeline
```

### 2. Set Up Environment Variables

Create or update the `.env` file in the `airflow/` directory with your WeatherStack API credentials:

```bash
# airflow/.env
WEATHER_API_KEY=your_api_key_here
WEATHER_API_BASE_URL=http://api.weatherstack.com/current
WEATHER_API_CITY=London
```

Replace `your_api_key_here` with your actual WeatherStack API key and customize the city as needed.

### 3. Start the Infrastructure

```bash
# Navigate to the project root
cd /path/to/weather_ETL_pipeline

# Start all services (PostgreSQL, Airflow, optional: Superset)
docker-compose up -d
```

This command will:
- Initialize PostgreSQL with required schemas
- Start Apache Airflow and its scheduler
- Set up Superset for visualization (if included in compose)

### 4. Access the Services

Once containers are running:

| Service | URL | Credentials |
|---------|-----|-------------|
| Airflow | http://localhost:8000 | Default (admin/admin) |
| PostgreSQL | localhost:5000 | `db_user` / `db_password` |
| Superset | http://localhost:8088 | root / root |

### 5. Trigger the Pipeline

In the Airflow UI:
1. Navigate to the DAGs section
2. Find the `weather_api_dbt_orchestrator` DAG
3. Click the play button to trigger a manual run, or wait for the scheduled execution (runs every 1 minute)

## Project Structure

### Airflow (`airflow/`)
- **dags/orchestrator.py** - Main DAG definition
  - `ingest_data_task` - Fetches weather data from API
  - `transform_data_task` - Runs dbt transformations

### API Request (`api_request/`)
- **api_request.py** - WeatherStack API client
  - `fetch_data()` - Retrieves weather data for specified city
  - Handles API authentication and error handling

- **insert_records.py** - Data loading module
  - Connects to PostgreSQL
  - Inserts raw weather data into database
  - Validates and logs data ingestion

### dbt Transformations (`dbt/myproject/`)

#### Models

- **staging/stg_weather_data.sql** - Raw data cleaning and standardization
- **mart/weather_report.sql** - Analytics-ready weather summary
- **mart/daily_average.sql** - Daily aggregated weather metrics

#### Transformation Flow

```
Raw API Data (api_data table)
         │
         ▼
staging/stg_weather_data.sql (Cleaned & standardized)
         │
         ├─────────────────────────────────┐
         │                                 │
         ▼                                 ▼
mart/weather_report.sql        mart/daily_average.sql
(Weather Summary)              (Daily Aggregates)
```

### Database Schemas

#### raw_api_data
Stores raw JSON responses from WeatherStack API:
- `temperature`
- `weather_description`
- `wind_speed`
- `humidity`
- `pressure`
- `precipitation`
- `weather_time_utc` / `weather_time_local`

#### staging
Cleaned and standardized data:
- Data type conversions
- Null handling
- Derived fields

#### mart
Business-ready analytics tables:
- Aggregated weather metrics
- Key measurements for reporting
- Indexed for fast queries

## Configuration

### Customizing the Pipeline

#### Change the City
Edit the environment variable in `airflow/.env`:
```bash
WEATHER_API_CITY=Paris  # or any other city
```

#### Change the Schedule
Edit `airflow/dags/orchestrator.py`:
```python
schedule=timedelta(minutes=1)  # Adjust frequency (hours, days, etc.)
```

#### Add More Data Sources
1. Create new API modules in `api_request/`
2. Add new tasks to the DAG in `airflow/dags/orchestrator.py`
3. Update dbt models to handle additional data

### Database Connection Details

The pipeline uses the following PostgreSQL connection string (auto-configured in compose):
```
postgresql+psycopg2://airflow:airflow@db:5432/airflow_db
```

For manual connections:
- **Host:** localhost
- **Port:** 5000
- **Database:** db
- **User:** db_user
- **Password:** db_password

## Monitoring & Debugging

### View Airflow Logs
```bash
docker-compose logs -f af  # Airflow service logs
```

### Access PostgreSQL
```bash
docker exec -it postgres_container psql -U db_user -d db
```

### Check dbt Compilation
dbt compilation logs are stored in:
```
dbt/myproject/logs/
```

### Troubleshoot Common Issues

**Issue:** API key not working
- Verify your WeatherStack API key is correct and active
- Check that the `.env` file is in the `airflow/` directory
- Restart Airflow container: `docker-compose restart af`

**Issue:** Database connection errors
- Ensure PostgreSQL container is running: `docker-compose ps`
- Verify port 5000 is available on your machine
- Check database credentials in `docker-compose.yaml`

**Issue:** dbt transformation failures
- Check dbt logs: `docker logs airflow_container | grep dbt`
- Verify database schema exists: `SELECT schema_name FROM information_schema.schemata;`
- Run dbt manually: `dbt debug` in the dbt directory

## Usage Examples

### Query Weather Data

Connect to PostgreSQL and run:

```sql
-- View latest weather data
SELECT * FROM public.weather_report 
ORDER BY weather_time_local DESC 
LIMIT 10;

-- Get daily average temperatures
SELECT * FROM public.daily_average 
ORDER BY weather_time_local DESC;
```

### Monitor Pipeline Runs

In Airflow UI:
1. Click on `weather_api_dbt_orchestrator` DAG
2. View **Tree View** for task dependencies
3. Check **Graph View** for visual pipeline
4. Monitor **Runs** section for execution history

### Extend Transformations

Add new dbt models in `dbt/myproject/models/mart/`:

```sql
{{ config(materialized='table') }}

SELECT
    city,
    DATE(weather_time_local) as date,
    AVG(temperature) as avg_temp,
    MAX(temperature) as max_temp,
    MIN(temperature) as min_temp
FROM {{ ref('stg_weather_data') }}
GROUP BY city, DATE(weather_time_local)
```

## Performance Optimization

### For High-Frequency Updates
- Adjust the Airflow schedule in `orchestrator.py`
- Implement incremental dbt models for faster transformations
- Use table materialization for frequently queried models

### For Large Datasets
- Implement partitioning in dbt models
- Add indexes on frequently filtered columns
- Use PostgreSQL materialized views for complex aggregations

## Contributing

1. Create a feature branch: `git checkout -b feature/new-weather-metric`
2. Make your changes (API updates, new dbt models, etc.)
3. Test locally with: `docker-compose up`
4. Commit and push: `git commit -am 'Add new feature'`
5. Create a pull request

## Troubleshooting & Support

For issues or questions:
1. Check the [Airflow Documentation](https://airflow.apache.org/docs/)
2. Review [dbt Documentation](https://docs.getbtlab.com/)
3. Check [WeatherStack API Docs](https://weatherstack.com/documentation)
4. Review Docker logs: `docker-compose logs`

## Maintenance

### Regular Tasks

**Weekly:**
- Monitor Airflow task failures in UI
- Check database disk usage: `docker exec postgres_container du -sh /var/lib/postgresql/data`

**Monthly:**
- Review dbt test results for data quality
- Analyze slow-running tasks and optimize queries
- Update Docker images: `docker-compose pull && docker-compose up -d`

**Quarterly:**
- Archive old weather data if needed
- Review and optimize dbt model performance
- Update API credentials if required

## Cleanup

To stop and remove all containers:

```bash
docker-compose down
```

To remove all data (WARNING: destructive):

```bash
docker-compose down -v
```

## License

This project is provided as-is for educational and production use.

## Acknowledgments

- WeatherStack for reliable weather data API
- Apache Airflow community for orchestration
- dbt labs for transformation framework
- PostgreSQL for robust database management

---

**Last Updated:** May 2026
**Version:** 1.0.0
