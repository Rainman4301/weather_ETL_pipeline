# Quick Start Guide - Data Reliability & Integrity Implementation

## What Changed?

### ✅ Your Requests Implemented

| Request | Solution | Location |
|---------|----------|----------|
| **Retry logic** | Exponential backoff decorator (3×, 5-60s) | insert_records.py |
| **Timeout handling** | Timeout context manager (30s DB ops) | insert_records.py |
| **Schema validation** | Spark schema validation before insert | insert_records.py |
| **Two DAGs** | Split into ingest (1hr) + transform (2hr) | airflow/dags/ |
| **Raw data saving** | All data → dev.raw_weather_data first | insert_records.py |
| **dbt staging copy** | dbt copies raw → staging with validation | dbt/models/staging/ |

---

## 4 New/Modified Files

### **1. airflow/dags/weather_data_ingestion.py** (NEW)
```
DAG: weather_data_ingestion
Schedule: Every 1 hour
Task: Generate data → Spark validate → Insert to raw_weather_data
Retry: 3 attempts, 5-min backoff
Timeout: 10 minutes
SLA: 15 minutes
```

### **2. airflow/dags/weather_data_transformation.py** (NEW)
```
DAG: weather_data_transformation  
Schedule: Every 2 hours (offset from ingest)
Task 1: Validate raw_weather_data (freshness, completeness)
Task 2: dbt run (raw → staging → intermediate → marts)
Retry: 2 attempts, 10-min backoff
Timeout: 30 minutes
SLA: 45 minutes
```

### **3. api_request/insert_records.py** (MODIFIED)
Added:
- `@retry_with_backoff(max_retries=3, base_delay=5)` decorator
- `timeout_context(timeout=30)` manager for DB operations
- `validate_records(records, spark)` function
- Structured error logging

No breaking changes - existing `main()` function works the same.

### **4. dbt models** (MODIFIED)
```
models/sources/sources.yml
  + Freshness: warn 90 min, error 120 min
  + Tests: unique, not_null, accepted_values

models/staging/stg_weather_data.sql
  + Contract enforcement (enforced: true)

models/staging/_stg_weather_data.yml (NEW)
  + Schema definition + data tests
  
models/staging/validate_raw_weather.sql (NEW)
  + Data quality query (optional, for Airflow)
```

---

## Retry & Timeout Configuration

```
Operation               Retries  Delay/Timeout    SLA
─────────────────────  ─────────────────────────────────
DB insert_chunk        3        30 sec timeout    N/A
Ingest DAG task        3        5 min backoff     15 min
Transform DAG task     2        10 min backoff    45 min
Data freshness         N/A      90/120 minutes    N/A
```

**Strategy:**
- Ingest: Quick, small, fail fast → 3 retries
- Transform: Slow, complex, be patient → 2 retries
- DB ops: Strict timeout to catch hangs

---

## Data Flow (After Changes)

```
┌─ HOURLY ─────────────────────┐
│ weather_data_ingestion       │
│ └─ ingest_data_task          │
│    Generate + Validate       │
│    └─ INSERT to              │
│       dev.raw_weather_data   │
└──────────────────────────────┘
        ↓ (stores raw data)
     
┌─ BI-HOURLY ──────────────────┐
│ weather_data_transformation   │
│ ├─ validate_raw_data         │
│ │  (check freshness)          │
│ └─ dbt_transform             │
│    ├─ stg_weather_data       │
│    ├─ silver_weather_data    │
│    └─ marts (hourly, daily)  │
└──────────────────────────────┘
```

---

## Testing the Changes

### Pre-Deployment

```bash
# 1. Check Python syntax
python3 -c "from api_request.insert_records import main, retry_with_backoff, validate_records"

# 2. Check Airflow DAGs
python3 airflow/dags/weather_data_ingestion.py
python3 airflow/dags/weather_data_transformation.py

# 3. Check dbt
cd dbt/myproject && dbt parse && dbt compile && dbt test
```

### Deployment

```bash
# 1. Copy new DAGs
cp airflow/dags/weather_data_ingestion.py $AIRFLOW_HOME/dags/
cp airflow/dags/weather_data_transformation.py $AIRFLOW_HOME/dags/

# 2. Pause old DAG
airflow dags pause weather_api_dbt_orchestrator

# 3. Test first run
airflow dags test weather_data_ingestion 2026-06-09
airflow dags test weather_data_transformation 2026-06-09

# 4. Monitor
airflow dags list
airflow logs weather_data_ingestion -1
```

---

## Key Features

### Reliability ✅
- **Automatic retry** with exponential backoff
- **Timeout protection** prevents hanging tasks
- **Clear error messages** with operation context
- **Independent DAGs** prevent cascading failures

### Integrity ✅
- **Spark schema validation** before insertion
- **dbt contracts** enforce column structure
- **Freshness checks** ensure data arrives on schedule
- **Data quality tests** catch bad data early

### Monitoring ✅
- **SLA tracking** (15 min ingest, 45 min transform)
- **Task retry logs** show all attempts
- **dbt test results** visible in logs
- **Validation failures** clearly logged

---

## Rollback (if needed)

```bash
# If ingest DAG causes issues
rm airflow/dags/weather_data_ingestion.py

# If transform DAG causes issues  
rm airflow/dags/weather_data_transformation.py

# If insert_records changes cause issues
git checkout HEAD -- api_request/insert_records.py

# Restore old DAG
airflow dags unpause weather_api_dbt_orchestrator
```

---

## Documentation

| File | Purpose |
|------|---------|
| **RELIABILITY_AND_INTEGRITY_GUIDE.md** | Complete implementation details |
| **IMPLEMENTATION_CHECKLIST.md** | Detailed verification checklist |
| **QUICK_START.md** | This file - 2-min overview |

---

## Questions?

**Q: How many times will a failing insert retry?**  
A: 3 times with exponential backoff: 5s, 10s, 20s, 60s delays.

**Q: What if transform DAG fails?**  
A: It retries 2 times, then alerts. Ingest DAG is unaffected.

**Q: How do I know if data quality is good?**  
A: Check dbt test results and validate_raw_data task logs.

**Q: Can I adjust retry/timeout values?**  
A: Yes! Edit `base_delay`, `max_retries` in insert_records.py, or `retry_delay`, `execution_timeout` in DAG files.

---

**Status:** ✅ Ready for deployment  
**Last Updated:** 2026-06-09
