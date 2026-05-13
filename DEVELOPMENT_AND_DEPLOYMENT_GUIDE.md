# Development & Deployment Complete Guide

This is your comprehensive guide for local development, CI/CD setup, and deployment to Azure.

---

## 📚 Quick Navigation

- **Just setting up locally?** → Jump to [Part 1: Local Development](#part-1-local-development-setup)
- **Need GitHub Secrets?** → See [GITHUB_SECRETS_SETUP.md](GITHUB_SECRETS_SETUP.md)
- **Ready for CI/CD?** → Jump to [Part 2: GitHub Workflow Setup](#part-2-github-workflow-setup)
- **Deploying to Azure?** → Jump to [Part 3: Azure VM Setup & Deployment](#part-3-azure-vm-setup--deployment)

---

# Part 1: Local Development Setup

Build and test your ETL pipeline locally in stages. Each session builds on the previous one.

## 🔧 Session 1: Docker & Database Foundation (30-45 min)

### Objectives
- Verify Docker is installed
- Start PostgreSQL container
- Confirm database connectivity

### Tasks

```bash
# 1. Verify Docker installation
docker --version
docker-compose --version

# 2. Validate compose file syntax
docker-compose config

# 3. Create required .env files (NEVER commit these!)

# Create airflow/.env
cat > airflow/.env << 'EOF'
AIRFLOW__CORE__LOAD_EXAMPLES=false
AIRFLOW__CORE__DAGS_FOLDER=/opt/airflow/dags
AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://airflow:airflow@db:5432/airflow_db
WEATHER_API_KEY=your_api_key_here
WEATHER_API_BASE_URL=http://api.weatherstack.com/current
WEATHER_API_CITY=London
EOF

# Create docker/.env
cat > docker/.env << 'EOF'
POSTGRES_PASSWORD=db_password
SUPERSET_ADMIN_PASSWORD=admin_password
SUPERSET_ADMIN_USERNAME=admin
SUPERSET_ADMIN_EMAIL=admin@example.com
EOF

# 4. Start only PostgreSQL first
docker-compose up -d db

# 5. Wait for startup (10-15 seconds)
sleep 15

# 6. Verify PostgreSQL is running
docker-compose ps

# 7. Test database connection
docker exec postgres_container psql -U db_user -d db -c "SELECT 1"
```

### ✅ Success Criteria
- `docker-compose config` validates without errors
- PostgreSQL container is running
- Database connection returns "1"

---

## 🗄️ Session 2: PostgreSQL Schemas & Tables (15-20 min)

### Objectives
- Verify database initialization
- Check all schemas are created
- Confirm tables structure

### Tasks

```bash
# 1. View initialization scripts execution
docker logs postgres_container | grep "BEGIN\|END\|CREATE"

# 2. List all schemas
docker exec postgres_container psql -U db_user -d db -c "\dn"

# 3. Verify Airflow database exists
docker exec postgres_container psql -U airflow -d airflow_db -c "\dt"

# 4. Check raw data schema
docker exec postgres_container psql -U db_user -d db -c "SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'api_%'"
```

### ✅ Success Criteria
- Both databases (`db` and `airflow_db`) exist
- All required schemas initialized
- No errors in init logs

---

## 🌐 Session 3: API Integration (20-30 min)

### Objectives
- Test API module locally
- Verify data extraction works
- Confirm data insertion

### Tasks

```bash
# 1. Navigate to API module
cd api_request

# 2. Test API call
python api_request.py
# Should return JSON weather data

# 3. Insert data into database
python insert_records.py

# 4. Verify data was inserted
cd ..
docker exec postgres_container psql -U db_user -d db -c "SELECT COUNT(*) FROM api_data.raw_weather_data;"

# Should return count > 0
```

### ✅ Success Criteria
- API returns weather data without errors
- Data inserts successfully
- Database count > 0

---

## 🔄 Session 4: Airflow Orchestration (30-45 min)

### Objectives
- Start Airflow service
- Validate DAG structure
- Test DAG execution

### Tasks

```bash
# 1. Start Airflow
docker-compose up -d af

# 2. Wait for initialization (30-45 seconds)
sleep 45

# 3. Check Airflow logs
docker logs airflow_container

# 4. List all DAGs
docker exec airflow_container airflow dags list

# 5. Check our DAG appears
docker exec airflow_container airflow dags list | grep weather_api_dbt

# 6. Test DAG execution (no schedule)
docker exec airflow_container airflow dags test weather_api_dbt_orchestrator 2026-05-10

# 7. Access Airflow UI
# Open: http://localhost:8000
# Login: admin/admin
```

### ✅ Success Criteria
- Airflow starts without errors
- DAG appears in list
- Manual test execution completes
- UI accessible

---

## 🔀 Session 5: dbt Data Transformation (45-60 min)

### Objectives
- Validate dbt models
- Run transformations
- Verify generated tables

### Tasks

```bash
# 1. Navigate to dbt project
cd dbt/myproject

# 2. Parse models (syntax check)
dbt parse --profiles-dir ../

# 3. Run dbt debug
dbt debug --profiles-dir ../

# 4. Generate documentation
dbt docs generate --profiles-dir ../

# 5. Run all transformations
dbt run --profiles-dir ../

# 6. Run tests
dbt test --profiles-dir ../

# 7. Check generated tables
cd ../..
docker exec postgres_container psql -U db_user -d db -c "\dt public.*"

# 8. Verify data in transformed tables
docker exec postgres_container psql -U db_user -d db -c "SELECT COUNT(*) FROM public.daily_average;"

cd dbt/myproject
```

### ✅ Success Criteria
- `dbt run` completes without errors
- All models compile successfully
- Tables appear in PostgreSQL
- `dbt test` passes (if tests exist)

---

## 🔗 Session 6: End-to-End Pipeline Test (30-45 min)

### Objectives
- Run complete pipeline (API → DB → dbt)
- Verify all components work together
- Check data flows through all layers

### Tasks

```bash
# 1. Ensure all services running
docker-compose ps
# Expected: db, af, superset running

# 2. Manually trigger DAG
docker exec airflow_container airflow dags test weather_api_dbt_orchestrator 2026-05-10

# 3. Monitor DAG execution
docker logs airflow_container | tail -50

# 4. Query data flow through all layers
docker exec postgres_container psql -U db_user -d db << 'EOF'
SELECT 'Raw' as layer, COUNT(*) FROM api_data.raw_weather_data
UNION ALL
SELECT 'Staging', COUNT(*) FROM public.stg_weather_data
UNION ALL
SELECT 'Mart', COUNT(*) FROM public.daily_average;
EOF

# 5. Check Airflow UI for task status
# http://localhost:8000
```

### ✅ Success Criteria
- All services running
- DAG executes both tasks (green status)
- Data flows through all 3 layers
- No errors in logs

---

## 📊 Session 7: Superset Visualization (Optional, 30-45 min)

### Objectives
- Start Superset
- Connect to PostgreSQL
- Create sample dashboard

### Tasks

```bash
# 1. Start Superset
docker-compose up -d superset

# 2. Wait for startup
sleep 30

# 3. Access Superset UI
# http://localhost:8088
# Login: admin/admin

# 4. In Superset UI, add PostgreSQL database:
#    - Settings → Database Connections
#    - Add Database → PostgreSQL
#    - Name: weather_db
#    - SQLAlchemy URI: postgresql://db_user:db_password@db:5432/db
#    - Test connection

# 5. Create dataset from public.daily_average
# 6. Create chart visualizing data
# 7. Add to dashboard
```

### ✅ Success Criteria
- Superset starts and UI loads
- PostgreSQL connection successful
- Can query dbt tables
- Dashboard displays data

---

---

# Part 2: GitHub Workflow Setup

## 🔐 Step 1: Add GitHub Secrets

Secrets are encrypted environment variables GitHub Actions uses for deployment.

**See [GITHUB_SECRETS_SETUP.md](GITHUB_SECRETS_SETUP.md) for complete instructions on adding all 7 secrets:**

1. `AZURE_VM_HOST` - Azure VM IP/hostname
2. `AZURE_VM_USER` - SSH username
3. `AZURE_VM_PRIVATE_KEY` - SSH private key file
4. `DB_PASSWORD` - PostgreSQL password
5. `WEATHER_API_KEY` - WeatherStack API key
6. `WEATHER_API_CITY` - City for weather
7. `SUPERSET_ADMIN_PASSWORD` - Superset admin password

---

## 🔄 Step 2: Understand the Workflow

### What Happens on Pull Request

When you create a PR to merge `expansion` → `main`:

```
Your Push → GitHub Actions Triggers → Automated Tests Run
├─ Install Python dependencies
├─ Validate Airflow DAGs syntax
├─ Lint Python code (flake8)
├─ Parse dbt models
├─ Test API connectivity
└─ Results appear as PR checks
```

You cannot merge until all checks pass ✓

### What Happens on Main Branch Push

After merging PR to `main`:

```
PR Merges → All Tests Run Again → Deployment Starts
├─ Stage 1: TEST (same as PR tests)
├─ Stage 2: BUILD (optional Docker build)
└─ Stage 3: DEPLOY
   ├─ SSH into Azure VM
   ├─ Pull latest code
   ├─ Update .env with secrets
   ├─ Restart Docker containers
   └─ Verify services running
```

---

## 🚀 Step 3: First Deployment Workflow

### 3.1 Create and Push Feature Branch

```bash
# Create feature branch
git checkout -b feature/setup-cicd

# Add any changes
git add .

# Commit
git commit -m "Add CI/CD setup documentation"

# Push to GitHub
git push origin feature/setup-cicd
```

### 3.2 Create Pull Request

```bash
# Via GitHub UI:
# 1. Go to github.com/Rainman4301/WeatherETL
# 2. Click "Compare & pull request"
# 3. Set base: main, compare: feature/setup-cicd
# 4. Add description
# 5. Click "Create pull request"

# OR via CLI:
gh pr create --base main --head feature/setup-cicd --title "Add CI/CD setup"
```

### 3.3 Wait for Tests

1. Go to your PR page
2. Scroll to **Checks** section
3. Wait for all checks to pass (green ✓)
4. Click on failing checks to see logs (if any fail)

### 3.4 Merge PR

Once all checks pass:

```bash
# Via GitHub UI:
# Click "Merge pull request" → "Confirm merge"

# OR via CLI:
gh pr merge [PR_NUMBER]
```

GitHub automatically triggers deployment to Azure VM!

---

### 3.5 Monitor Deployment

```bash
# Watch deployment progress
gh run list

# View latest run
gh run view --latest

# Stream logs
gh run view [RUN_ID] --log

# Check specific job
gh run view [RUN_ID] -j deploy
```

---

---

# Part 3: Azure VM Setup & Deployment

## ⚙️ Azure VM Preparation (One-Time Setup)

### Step 1: Install Docker & Utilities

SSH into your Azure VM:

```bash
ssh azureuser@your-vm-ip

# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker & Docker Compose
sudo apt-get install -y docker.io docker-compose git curl

# Add user to docker group
sudo usermod -aG docker $(whoami)
newgrp docker

# Verify installation
docker --version
docker-compose --version
git --version
```

### Step 2: Clone Repository

```bash
# Clone repo
git clone https://github.com/Rainman4301/WeatherETL.git
cd WeatherETL

# Checkout main branch
git checkout main

# Create data directory
mkdir -p postgres/data
chmod -R 777 postgres/data
```

### Step 3: Create Local .env Files

⚠️ These are created MANUALLY with actual secrets, not by CI/CD:

```bash
# Create airflow/.env with your secrets
cat > airflow/.env << 'EOF'
AIRFLOW__CORE__LOAD_EXAMPLES=false
AIRFLOW__CORE__DAGS_FOLDER=/opt/airflow/dags
AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://airflow:airflow@db:5432/airflow_db
WEATHER_API_KEY=YOUR_ACTUAL_API_KEY
WEATHER_API_CITY=London
EOF

# Create docker/.env with your secrets
cat > docker/.env << 'EOF'
POSTGRES_PASSWORD=YOUR_DB_PASSWORD
SUPERSET_ADMIN_PASSWORD=YOUR_SUPERSET_PASSWORD
SUPERSET_ADMIN_USERNAME=admin
SUPERSET_ADMIN_EMAIL=admin@example.com
EOF

# Verify .env in .gitignore
grep "\.env" .gitignore
```

### Step 4: Test Manual Startup

```bash
# Start services
docker-compose up -d

# Wait for initialization
sleep 60

# Check all running
docker-compose ps

# Test services
curl http://localhost:8000  # Airflow
curl http://localhost:8088  # Superset
```

---

## 🚀 First Deployment from GitHub

After merging your PR to `main`:

1. GitHub Actions automatically runs tests
2. If all tests pass ✓, deployment starts
3. CI/CD workflow SSH's into your Azure VM and:
   - Pulls latest code (`git pull origin main`)
   - Updates `.env` files with secrets from GitHub
   - Restarts Docker containers
   - Verifies all services running

### Monitor Deployment

```bash
# From your local machine
gh run list
gh run view --latest --log

# From Azure VM
ssh azureuser@your-vm-ip
docker-compose ps
docker-compose logs --tail=20
```

---

## 🔍 Verify Deployment Success

SSH into Azure VM and check:

```bash
# All services running?
docker-compose ps
# Expected: db, af, superset all UP

# Check logs for errors
docker-compose logs | grep -i error

# Test API endpoint
curl http://localhost:8000/health

# Test database
docker exec postgres_container psql -U db_user -d db -c "SELECT 1"

# Check Airflow DAGs loaded
docker exec airflow_container airflow dags list | grep weather
```

---

---

# Part 4: Development Workflow

## 📝 Normal Development Cycle

```bash
# 1. Create feature branch
git checkout -b feature/your-feature-name

# 2. Make code changes
# ... edit files ...

# 3. Test locally (Session 1-6)
docker-compose ps
docker-compose logs

# 4. Commit changes
git add .
git commit -m "Descriptive commit message"

# 5. Push to GitHub
git push origin feature/your-feature-name

# 6. Create PR
gh pr create --base main --head feature/your-feature-name

# 7. Wait for tests to pass
# → Check GitHub Actions tab
# → Click on workflow to see results

# 8. After tests pass, merge
gh pr merge [PR_NUMBER]

# 9. Deployment automatically starts!
# → Monitor via: gh run view --latest --log
```

---

## 🐛 Troubleshooting

### Tests Fail on PR

**Problem:** Red X on PR checks

**Solution:**
1. Click "Details" on the failed check
2. Review the error message
3. Fix code locally
4. Commit and push to same branch
5. Tests automatically re-run

### Services Won't Start Locally

```bash
# Check if ports are in use
lsof -i :5000    # PostgreSQL
lsof -i :8000    # Airflow
lsof -i :8088    # Superset

# Remove old containers
docker-compose down -v

# Rebuild and start
docker-compose up -d

# Check logs
docker-compose logs
```

### SSH Deployment Fails

**"Permission denied (publickey)"**
- Verify `AZURE_VM_PRIVATE_KEY` secret is complete
- Test locally: `ssh -i ~/.ssh/azure_vm_key azureuser@your-vm-ip`
- Ensure public key is on Azure VM

---

## 📊 Monitoring & Maintenance

### Check Workflow Status

```bash
# List all workflow runs
gh run list

# View specific run
gh run view [RUN_ID]

# View run logs
gh run view [RUN_ID] --log

# Cancel a run
gh run cancel [RUN_ID]
```

### Check Azure VM Services

```bash
# SSH into VM
ssh azureuser@your-vm-ip

# All services running?
docker-compose ps

# View logs
docker-compose logs --tail=50

# Specific service logs
docker logs airflow_container | tail -100

# Restart a service
docker-compose restart af
```

### Database Health Check

```bash
docker exec postgres_container psql -U db_user -d db << 'EOF'
-- Check table sizes
SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) as size
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(relid) DESC;

-- Check recent data
SELECT COUNT(*) FROM api_data.raw_weather_data;
SELECT COUNT(*) FROM public.daily_average;
EOF
```

---

## 🔐 Security Reminders

**DO** ✅
- Store `.env` files only locally (in `.gitignore`)
- Use GitHub Secrets for all credentials
- Rotate secrets regularly
- Keep SSH private key secure
- Different credentials for different environments

**DON'T** ❌
- Commit `.env` files to Git
- Hardcode secrets in code
- Share SSH keys via email
- Use weak passwords
- Reuse credentials across projects

---

## 🎯 Checklist for First Full Deployment

- [ ] Docker installed locally and on Azure VM
- [ ] All 7 GitHub Secrets added
- [ ] SSH key tested locally
- [ ] All Sessions 1-6 completed locally
- [ ] Feature branch created and pushed
- [ ] PR created with all checks passing
- [ ] PR merged to main
- [ ] Deployment job started automatically
- [ ] Services running on Azure VM
- [ ] Can access Airflow UI (http://vm-ip:8000)
- [ ] Can access Superset UI (http://vm-ip:8088)
- [ ] Data flowing through complete pipeline

---

## 📚 Quick Command Reference

```bash
# Local Development
docker-compose up -d              # Start services
docker-compose down               # Stop services
docker-compose ps                 # Check status
docker-compose logs -f            # View logs

# Airflow
docker exec af airflow dags list              # List DAGs
docker exec af airflow dags test weather_api_dbt_orchestrator 2026-05-10  # Test DAG

# dbt
cd dbt/myproject
dbt run --profiles-dir ../        # Run transformations
dbt test --profiles-dir ../       # Run tests
dbt parse --profiles-dir ../      # Check syntax

# Git & GitHub
git checkout -b feature/name      # New branch
git push origin feature/name      # Push to GitHub
gh pr create --base main          # Create PR
gh run list                       # View CI/CD runs

# Azure VM
ssh azureuser@vm-ip               # SSH into VM
docker-compose ps                 # Check services
docker-compose logs               # View logs
```

---

**Ready to deploy? Start with Part 1 for local setup, then follow Part 2 for GitHub workflow!** 🚀
