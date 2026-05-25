# Development & Deployment Guide

---

## Quick Navigation

- **Setting up locally?** → Part 1: Local Development
- **Need GitHub secrets?** → GITHUB_SECRETS_SETUP.md
- **Understanding CI/CD?** → Part 2: GitHub Actions Workflow
- **Deploying to Azure?** → Part 3: Azure VM Setup

---

# Part 1: Local Development

Six services work together in Docker Compose:

| Container | Image | Port | Role |
|-----------|-------|------|------|
| `postgres_container` | postgres:14.17 | 5000→5432 | Main data warehouse |
| `airflow_container` | apache/airflow:3.0.0 | 8000→8080 | Orchestration |
| `dbt_container` | ghcr.io/dbt-labs/dbt-postgres:1.9.0 | — | Transformation (on-demand) |
| `superset_container` | apache/superset:3.0.0-py310 | 8088→8088 | Dashboards |
| `superset_init_container` | apache/superset:3.0.0-py310 | — | One-time Superset setup |
| `redis` | redis:7 | 6379 | Superset cache broker |

---

## Session 1: Environment Setup

### Prerequisites

```bash
docker --version          # Docker 20+
docker compose version    # Compose v2
python3 --version         # 3.10+
```

### Create .env files

These hold secrets locally and are git-ignored. Never commit them.

```bash
# airflow/.env — used by Airflow and insert_records.py
cat > airflow/.env << 'EOF'
WEATHER_API_BASE_URL=http://api.weatherstack.com/current
WEATHER_API_KEY=your_api_key_here
WEATHER_API_CITY=London
EOF
```

For `docker/.env`, fill in values for `DATABASE_PASSWORD`, `POSTGRES_PASSWORD`, `SUPERSET_SECRET_KEY` (`openssl rand -base64 42`), and `ADMIN_PASSWORD`. See the full variable list in `docker-compose.yaml`.

---

## Session 2: Start the Database

```bash
docker compose up -d db

# Wait until healthy
docker compose ps
# Expected: postgres_container   Up (healthy)

# Verify the dev schema was created by the init script
docker exec postgres_container psql -U db_user -d db -c "\dn"

# Verify the weather table structure
docker exec postgres_container psql -U db_user -d db \
  -c "SELECT column_name FROM information_schema.columns WHERE table_name = 'raw_weather_data';"
```

---

## Session 3: Test Data Ingestion

`insert_records.py` has two modes: `use_random_data=True` (default — 10 cities, synthetic data, no API key needed) or `use_random_data=False` (real WeatherStack API).

```bash
pip install psycopg2-binary requests

export DB_HOST=localhost
export DB_PORT=5000        # mapped port from docker-compose.yaml
export DB_NAME=db
export DB_USER=db_user
export DB_PASSWORD=db_password

cd api_request
python insert_records.py

# Verify
docker exec postgres_container psql -U db_user -d db \
  -c "SELECT city, COUNT(*) FROM dev.raw_weather_data GROUP BY city ORDER BY city;"
```

Expected: 10 rows, one per city.

---

## Session 4: Start Airflow

```bash
docker compose up -d af

# First run takes 30-60s
docker logs -f airflow_container
# Ready when you see: "Airflow is ready"

docker exec airflow_container airflow dags list-import-errors
# Expected: No data found  (no errors)

docker exec airflow_container airflow dags list | grep weather_api_dbt
```

Open `http://localhost:8000` — login with `admin` and the password set in `_AIRFLOW_WWW_USER_PASSWORD` in `docker-compose.yaml`.

The DAG `weather_api_dbt_orchestrator` runs every 30 minutes with two tasks:
- **`ingest_data_task`** — PythonOperator calling `insert_records.main()`
- **`transform_data_task`** — DockerOperator running `dbt run` in a fresh `dbt-postgres:1.9.0` container

```bash
# Trigger manually
docker exec airflow_container airflow dags trigger weather_api_dbt_orchestrator
```

---

## Session 5: dbt Transformations

```bash
docker compose run --rm dbt dbt parse
docker compose run --rm dbt dbt run
docker compose run --rm dbt dbt test

# Interactive shell
docker compose run --rm dbt bash
```

Three-layer medallion architecture:

```
dev.raw_weather_data              <- written by insert_records.py
        |
staging.stg_weather_data          <- incremental load from raw
        |
intermediate.silver_weather_data  <- dedup + UTC-to-local TZ conversion
        |
mart.daily_average                <- daily aggregates per city
mart.hourly_weather               <- full hourly detail
mart.weather_report               <- all records for reporting
mart.city_summary                 <- latest single row per city
```

Verify data flow:

```bash
docker exec postgres_container psql -U db_user -d db -c "
  SELECT 'raw'     AS layer, COUNT(*) FROM dev.raw_weather_data
  UNION ALL
  SELECT 'staging',           COUNT(*) FROM staging.stg_weather_data
  UNION ALL
  SELECT 'silver',            COUNT(*) FROM intermediate.silver_weather_data
  UNION ALL
  SELECT 'daily_avg',         COUNT(*) FROM mart.daily_average;"
```

---

## Session 6: Superset Dashboards

```bash
docker compose up -d superset redis

# Wait for init to complete
docker logs superset_init_container -f
# Done when: "Init Done!"

# UI at http://localhost:8088
# Login: admin / ADMIN_PASSWORD from docker/.env
```

Add a database connection in Superset:
- Settings -> Database Connections -> + Database -> PostgreSQL
- URI: `postgresql://db_user:db_password@db:5432/db`
- Test connection -> Save

Create datasets from the mart tables. `mart.city_summary` is the best starting point for a city-filtered dashboard.

---

## Session 7: End-to-End Verification

```bash
docker compose ps   # all services up?

docker exec airflow_container airflow dags trigger weather_api_dbt_orchestrator

# Watch task states
docker logs airflow_container -f | grep -E "task_id|state|ERROR"

# After both tasks succeed
docker exec postgres_container psql -U db_user -d db \
  -c "SELECT city, weather_time_local, temperature FROM mart.city_summary ORDER BY city;"
```

---

# Part 2: GitHub Actions Workflow

Defined in `.github/workflows/deploy.yml`. Three jobs.

## Pipeline Structure

```
Every push / PR -> [test]
  |- Python 3.10 + pip install
  |- flake8 lint api_request/ (syntax only, non-blocking)
  |- airflow db migrate + dags list-import-errors
  |- dbt parse --profiles-dir ../
  |- pytest api_request/ -v
  +- psycopg2 connectivity check against ephemeral postgres:14.17

Push to main (after test passes) -> [deploy]
  |- SSH into Azure VM
  |- git fetch origin main + reset --hard
  |- Write airflow/.env from GitHub Secrets
  |- Write docker/.env from GitHub Secrets (30+ variables)
  |- docker compose down
  |- docker compose pull
  |- docker compose up -d
  |- sleep 30
  +- docker compose ps

Always -> [notify]
  |- Report test result
  +- Report deploy result (or "skipped" if not a main push)
```

## Normal Development Flow

```bash
git checkout -b feature/your-feature

# Make changes, test locally

git add .
git commit -m "your message"
git push origin feature/your-feature
# test job fires automatically

# Open PR on GitHub -> all checks must be green to merge
# Merge to main -> deploy fires automatically
```

## Reading CI Logs

| Failure | Likely Cause | Fix |
|---------|-------------|-----|
| `dbt parse` fails | Model YAML syntax error | Fix the YAML, push again |
| `dags list-import-errors` has output | Python import error in orchestrator.py | Check dependencies |
| `pytest` fails | Test assertion broke | Fix `api_request/tests/` |
| Deploy SSH fails | Key or host secret misconfigured | Check GitHub Secrets |

---

# Part 3: Azure VM Setup

One-time setup. After this, all deployments are handled by GitHub Actions.

## Step 1: Install Docker

```bash
ssh azureuser@your-vm-ip

sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

sudo usermod -aG docker $USER
newgrp docker
docker compose version
```

## Step 2: Check the Docker socket group ID

The Airflow container mounts `/var/run/docker.sock` to run the dbt DockerOperator. `docker-compose.yaml` adds group IDs `1001` and `988`. Verify your VM's actual docker GID:

```bash
getent group docker
# e.g. docker:x:988:azureuser
```

If different, update `group_add` in `docker-compose.yaml` before deploying.

## Step 3: Clone the repository

```bash
cd ~
git clone https://github.com/Rainman4301/weather_ETL_pipeline.git
cd weather_ETL_pipeline
git checkout main
```

## Step 4: Create .env files for first startup

```bash
echo "WEATHER_API_BASE_URL=http://api.weatherstack.com/current" > airflow/.env
echo "WEATHER_API_KEY=your_actual_key" >> airflow/.env
echo "WEATHER_API_CITY=London" >> airflow/.env
# Fill in docker/.env with all required variables
```

## Step 5: First startup

```bash
docker compose up -d
sleep 60
docker compose ps
# All containers should show "Up" or "Up (healthy)"
```

Services:
- Airflow: `http://your-vm-ip:8000`
- Superset: `http://your-vm-ip:8088`

All future deployments are handled automatically on every push to `main`.

---

## Cloudflare Tunnel

Exposes Superset publicly without opening inbound firewall ports. `cloudflared` establishes an outbound-only connection — Cloudflare handles DNS and SSL/TLS.

```bash
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb \
  -o cloudflared.deb
sudo dpkg -i cloudflared.deb

cloudflared tunnel login
cloudflared tunnel create weather-pipeline

cat > ~/.cloudflared/config.yml << 'EOF'
tunnel: <your-tunnel-id>
credentials-file: /root/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: superset.yourdomain.com
    service: http://localhost:8088
  - service: http_status:404
EOF

sudo cloudflared service install
sudo systemctl start cloudflared
```

Add a CNAME in Cloudflare DNS: `superset.yourdomain.com` -> `<tunnel-id>.cfargotunnel.com`. HTTPS is automatic.

---

## Troubleshooting

**DockerOperator fails: cannot connect to Docker daemon**
Check the socket group ID (Step 2).

**dbt task fails: profile not found**
`orchestrator.py` discovers the host path by inspecting the Airflow container's mounts. Verify the volume is mounted at `/opt/airflow/dags`:
```bash
docker inspect airflow_container | grep -A5 Mounts
```

**Containers restarting after deploy**
```bash
docker logs <container_name> --tail 50
```
Usually a missing variable in a `.env` file — check all 10 secrets are set in GitHub.

**Services not accessible after deploy**
The deploy script uses `sleep 30`. If still starting, check from the VM:
```bash
ssh azureuser@your-vm-ip "cd ~/weather_ETL_pipeline && docker compose ps"
```

---

## Quick Reference

```bash
# Local
docker compose up -d                            # Start everything
docker compose up -d db af                      # Start specific services
docker compose down                             # Stop all
docker compose logs -f airflow_container        # Tail Airflow logs
docker compose ps                               # Status

# Airflow
docker exec airflow_container airflow dags list
docker exec airflow_container airflow dags list-import-errors
docker exec airflow_container airflow dags trigger weather_api_dbt_orchestrator

# dbt
docker compose run --rm dbt dbt parse
docker compose run --rm dbt dbt run
docker compose run --rm dbt dbt test

# Postgres
docker exec postgres_container psql -U db_user -d db \
  -c "SELECT COUNT(*) FROM dev.raw_weather_data;"

# Azure VM (from local)
ssh azureuser@your-vm-ip "cd ~/weather_ETL_pipeline && docker compose ps"
```