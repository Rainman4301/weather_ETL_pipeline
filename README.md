# Weather ETL Pipeline

A production-grade weather data pipeline running on Azure VM — ingesting data from the WeatherStack API every 30 minutes, transforming it through a three-layer dbt model, and serving live dashboards via Apache Superset.

**Live dashboard:** [superset.rainsunny.org](https://superset.rainsunny.org/superset/dashboard/1/)

---

## Architecture

```
WeatherStack API
      |
      v
Airflow 3.0  (PythonOperator — insert_records.py)
      |
      v
PostgreSQL 14  (dev.raw_weather_data)
      |
      v
dbt 1.9  (DockerOperator)
  staging.stg_weather_data         <- incremental load
  intermediate.silver_weather_data <- dedup + UTC-to-local TZ
  mart.daily_average               <- daily aggregates
  mart.hourly_weather              <- full hourly detail
  mart.weather_report              <- all records for reporting
  mart.city_summary                <- latest row per city
      |
      v
Apache Superset 3.0  (dashboards)
      |
      v
Cloudflare Tunnel  (public HTTPS — no open firewall ports)
```

Six services are managed by Docker Compose on an Azure VM. A GitHub Actions CI/CD pipeline validates every push and deploys to the VM on merge to `main`.

---

## Stack

| Layer | Technology |
|-------|-----------|
| Orchestration | Apache Airflow 3.0.0 |
| Database | PostgreSQL 14.17 |
| Transformation | dbt-postgres 1.9.0 |
| Visualisation | Apache Superset 3.0.0 |
| Cache | Redis 7 |
| Containerisation | Docker Compose |
| CI/CD | GitHub Actions |
| Infrastructure | Azure VM (Ubuntu) |
| Public access | Cloudflare Tunnel |

---

## Repository Structure

```
weather_ETL_pipeline/
|
|-- .github/
|   +-- workflows/
|       +-- deploy.yml          # CI/CD: test on every push, deploy on main
|
|-- airflow/
|   |-- dags/
|   |   +-- orchestrator.py     # DAG definition (PythonOperator + DockerOperator)
|   +-- .env                    # git-ignored: WEATHER_API_KEY, city, base URL
|
|-- api_request/
|   |-- api_request.py          # WeatherStack API client
|   |-- insert_records.py       # DB ingestion (random or live API mode)
|   +-- tests/
|       +-- test_api.py         # pytest unit tests
|
|-- dbt/
|   |-- myproject/
|   |   |-- models/
|   |   |   |-- staging/        # stg_weather_data (incremental)
|   |   |   |-- intermediate/   # silver_weather_data (dedup + TZ)
|   |   |   +-- mart/           # daily_average, hourly_weather, weather_report, city_summary
|   |   +-- dbt_project.yml
|   +-- profiles.yml            # DB connection (reads from env vars)
|
|-- docker/
|   |-- .env                    # git-ignored: all Superset + DB secrets
|   |-- docker-bootstrap.sh
|   |-- docker-init.sh
|   +-- superset_config.py
|
|-- postgres/
|   |-- airflow_init.sql        # Creates airflow_db + airflow user
|   +-- superset_init.sql       # Creates superset_db + superset user
|
+-- docker-compose.yaml
```

---

## Quick Start

### Prerequisites

- Docker + Docker Compose v2 (`docker compose version`)
- Python 3.10+
- A WeatherStack API key ([free tier](https://weatherstack.com))

### 1. Clone

```bash
git clone https://github.com/Rainman4301/weather_ETL_pipeline.git
cd weather_ETL_pipeline
```

### 2. Create .env files

These are git-ignored and must be created manually.

```bash
# airflow/.env
cat > airflow/.env << 'EOF'
WEATHER_API_BASE_URL=http://api.weatherstack.com/current
WEATHER_API_KEY=your_api_key_here
WEATHER_API_CITY=London
EOF
```

For `docker/.env`, copy the template and fill in passwords and secret keys:

```bash
cp docker/.env.example docker/.env
# Edit docker/.env: DATABASE_PASSWORD, POSTGRES_PASSWORD, SUPERSET_SECRET_KEY, ADMIN_PASSWORD
```

### 3. Start services

```bash
# Start database first (everything depends on its health check)
docker compose up -d db
docker compose ps   # wait until: Up (healthy)

# Start everything
docker compose up -d
```

### 4. Access

| Service | URL | Login |
|---------|-----|-------|
| Airflow | http://localhost:8000 | admin / see `_AIRFLOW_WWW_USER_PASSWORD` in compose |
| Superset | http://localhost:8088 | admin / `ADMIN_PASSWORD` from docker/.env |
| PostgreSQL | localhost:5000 | db_user / db_password |

### 5. Trigger the pipeline

In the Airflow UI, find `weather_api_dbt_orchestrator` and click ▶, or:

```bash
docker exec airflow_container airflow dags trigger weather_api_dbt_orchestrator
```

The DAG runs on a 30-minute schedule. Task 1 ingests data; Task 2 runs dbt transformations via DockerOperator.

---

## Data Ingestion Modes

`insert_records.py` supports two modes controlled by the `use_random_data` flag:

**Random mode** (default, `use_random_data=True`) — generates synthetic data for 10 cities at 30-minute intervals: 24h of historical records + 7 days of forecasts. No API key needed. Good for development and testing.

**Live API mode** (`use_random_data=False`) — fetches real current conditions from WeatherStack for the city set in `WEATHER_API_CITY`. Requires a valid API key.

To switch modes, edit the `main()` call at the bottom of `insert_records.py`:

```python
if __name__ == "__main__":
    main(use_random_data=False, days_ahead=7)
```

---

## dbt Models

### Incremental strategy

`stg_weather_data` and `silver_weather_data` both use `incremental` materialisation — each run only processes rows with `inserted_at` newer than the last run, keeping transformation time constant as data grows.

### Deduplication

`silver_weather_data` deduplicates on `(city, time)` using `row_number() over (partition by city, time order by inserted_at desc)`, keeping the most recently inserted record for each city/time combination.

### Timezone conversion

The raw data stores `time` in UTC. `silver_weather_data` adds `weather_time_local` by casting the `utc_offset` column as an interval:

```sql
(time + (utc_offset || ' hours')::interval) as weather_time_local
```

### Running dbt manually

```bash
docker compose run --rm dbt dbt parse
docker compose run --rm dbt dbt run
docker compose run --rm dbt dbt test
```

---

## CI/CD Pipeline

Defined in `.github/workflows/deploy.yml`.

**On every push and PR:**
- Python 3.10 + dependency install
- `flake8` lint on `api_request/` (syntax errors only)
- `airflow db migrate` + `dags list-import-errors`
- `dbt parse --profiles-dir ../`
- `pytest api_request/ -v`
- `psycopg2` connectivity check against an ephemeral Postgres container

**On push to `main` (after all tests pass):**
- SSH into Azure VM
- `git fetch origin main && git reset --hard`
- Write `airflow/.env` and `docker/.env` from GitHub Secrets
- `docker compose down && docker compose pull && docker compose up -d`

Secrets are never stored in the repository. See [GITHUB_SECRETS_SETUP.md](GITHUB_SECRETS_SETUP.md) for the full list of required secrets.

---

## Public Access via Cloudflare Tunnel

The Superset dashboard is publicly accessible at [superset.rainsunny.org](https://superset.rainsunny.org/superset/dashboard/1/) via Cloudflare Tunnel. `cloudflared` establishes an outbound-only persistent connection from the VM to Cloudflare's edge — no inbound firewall ports are open, and Cloudflare handles DNS, SSL/TLS, DDoS protection, and bot mitigation automatically.

---

## Querying the Data

```sql
-- Latest conditions per city
SELECT city, temperature, weather_description, weather_time_local
FROM mart.city_summary
ORDER BY city;

-- Daily averages for Sydney
SELECT date, avg_temperature, avg_humidity, avg_wind_speed
FROM mart.daily_average
WHERE city = 'Sydney'
ORDER BY date DESC;

-- Forecast data only (next 7 days)
SELECT city, weather_time_local, temperature, precipitation_prob
FROM mart.hourly_weather
WHERE is_forecast = TRUE
ORDER BY city, weather_time_local;
```

---

## Monitoring

```bash
# Container status
docker compose ps

# Airflow task logs
docker logs airflow_container --tail 50

# dbt run output (most recent transform task)
docker logs airflow_container | grep -A 20 "transform_data_task"

# Database record counts
docker exec postgres_container psql -U db_user -d db -c "
  SELECT 'raw'     AS layer, COUNT(*) FROM dev.raw_weather_data
  UNION ALL
  SELECT 'staging',           COUNT(*) FROM staging.stg_weather_data
  UNION ALL
  SELECT 'silver',            COUNT(*) FROM intermediate.silver_weather_data
  UNION ALL
  SELECT 'mart_daily',        COUNT(*) FROM mart.daily_average;"
```

---

## Troubleshooting

**`dbt transform_data_task` fails**
Check that the `HOST_REPO_PATH` resolved correctly. `orchestrator.py` discovers the host path by inspecting the Airflow container's mounts via the Docker socket. Verify:
```bash
docker inspect airflow_container | grep -A5 Mounts
```

**Airflow shows DAG import errors**
```bash
docker exec airflow_container airflow dags list-import-errors
```

**Superset can't connect to the database**
Use the internal Docker network hostname — `db` not `localhost`:
```
postgresql://db_user:db_password@db:5432/db
```

**Containers restart after deploy**
A missing or malformed `.env` variable. Check logs:
```bash
docker logs <container_name> --tail 30
```

---

## Documentation

- [GITHUB_SECRETS_SETUP.md](GITHUB_SECRETS_SETUP.md) — all 10 required secrets and how to get them
- [DEVELOPMENT_AND_DEPLOYMENT_GUIDE.md](DEVELOPMENT_AND_DEPLOYMENT_GUIDE.md) — full local setup walkthrough, CI/CD details, and Azure VM provisioning
- [GITIGNORE_GUIDE.md](GITIGNORE_GUIDE.md) — what's ignored and why

---

## Known Limitations & Roadmap

- **Executor:** Currently uses Airflow `LocalExecutor`. For higher parallelism, migrate to `CeleryExecutor` with Redis workers or `KubernetesExecutor`.
- **API schema gap:** Random data generator populates all columns; the live API path (`insert_record()`) inserts a subset. Full column parity needed before switching to live mode.
- **`sleep 30` in deploy:** Fragile startup check. A health-poll loop would be more reliable.
- **dbt tests:** Only `not_null` and `accepted_values` currently. Adding `dbt-utils` range tests and custom singular tests would improve data quality confidence.

---

*Built with Airflow · dbt · PostgreSQL · Superset · Docker · GitHub Actions · Azure · Cloudflare*