# Implementation Index - Data Reliability & Integrity

## 📚 Documentation (Read These First)

Start with one of these based on your time:

| Document | Time | Best For |
|----------|------|----------|
| **QUICK_START.md** | 2 min | "Just tell me what changed" |
| **RELIABILITY_AND_INTEGRITY_GUIDE.md** | 10 min | "I want the full story" |
| **IMPLEMENTATION_CHECKLIST.md** | 5 min | "Verification & deployment steps" |

---

## 📁 Files Modified (3 files)

### 1. `api_request/insert_records.py`
**What changed:** Added retry logic, timeout protection, schema validation  
**Why:** Enable automatic retry with exponential backoff, prevent hanging ops, validate data before insert  
**Impact:** ✅ Backward compatible - `main()` function signature unchanged

**Key additions:**
- `@retry_with_backoff(max_retries=3, base_delay=5)` - decorator for exponential backoff
- `@contextmanager timeout_context(operation, timeout=30)` - timeout protection
- `validate_records(records, spark)` - Spark schema validation function
- Applied to: `insert_chunk()`, `connect_to_db()`, `create_table()`

**How to verify:** 
```bash
python3 -c "from api_request.insert_records import retry_with_backoff, timeout_context, validate_records; print('✓ All functions imported')"
```

---

### 2. `dbt/myproject/models/sources/sources.yml`
**What changed:** Added freshness checks and column tests  
**Why:** Ensure data arrives on schedule and contains valid values  
**Impact:** ✅ dbt will now validate source quality

**Key additions:**
```yaml
sources:
  - name: dev
    freshness:
      warn_after: {count: 90, period: minute}
      error_after: {count: 120, period: minute}
    loaded_at_field: inserted_at
    tables:
      - name: raw_weather_data
        columns:
          - name: id
            tests:
              - unique
              - not_null
          # ... more tests
```

**How to verify:**
```bash
cd dbt/myproject && dbt parse && echo "✓ YAML syntax OK"
```

---

### 3. `dbt/myproject/models/staging/stg_weather_data.sql`
**What changed:** Added contract enforcement  
**Why:** Enforce schema structure - prevent breaking changes to column definitions  
**Impact:** ✅ dbt will fail if column names/types don't match contract

**Key additions:**
```sql
{{ config(
    materialized='incremental',
    contract={
        "enforced": true  # <-- NEW: Contract enforcement
    },
    unique_key='id',
    post_hook="DELETE FROM {{ this }} WHERE inserted_at < NOW() - INTERVAL '30 days'"
) }}
```

**How to verify:**
```bash
cd dbt/myproject && dbt compile --select stg_weather_data && echo "✓ Contract OK"
```

---

## 📁 Files Created (4 files)

### 1. `airflow/dags/weather_data_ingestion.py` (NEW)
**Purpose:** Hourly raw data generation  
**Schedule:** Every 1 hour  
**Task:** Generate + validate + insert to `dev.raw_weather_data`  
**Retry:** 3 attempts, 5 min backoff  
**Timeout:** 10 minutes  
**SLA:** 15 minutes  

**Key code:**
```python
dag = DAG(
    dag_id='weather_data_ingestion',
    schedule=timedelta(hours=1),
    default_args={'retries': 3, 'retry_delay': timedelta(minutes=5)},
)

with dag:
    task = PythonOperator(
        task_id='ingest_data_task',
        python_callable=main,  # from insert_records.py
        execution_timeout=timedelta(minutes=10),
        sla=timedelta(minutes=15),
    )
```

**How to verify:**
```bash
python3 -c "exec(open('airflow/dags/weather_data_ingestion.py').read()); print('✓ DAG defined')"
```

---

### 2. `airflow/dags/weather_data_transformation.py` (NEW)
**Purpose:** Bi-hourly validation + dbt transformation  
**Schedule:** Every 2 hours (offset)  
**Task 1:** Validate `dev.raw_weather_data` (freshness, completeness)  
**Task 2:** Run dbt (staging → intermediate → marts)  
**Retry:** 2 attempts, 10 min backoff  
**Timeout:** 30 minutes  
**SLA:** 45 minutes  

**Key code:**
```python
dag = DAG(
    dag_id='weather_data_transformation',
    schedule=timedelta(hours=2),
    default_args={'retries': 2, 'retry_delay': timedelta(minutes=10)},
)

with dag:
    validate_task = PythonOperator(
        task_id='validate_raw_data',
        python_callable=validate_raw_data,
    )
    dbt_task = DockerOperator(...)
    
    validate_task >> dbt_task  # Validate before transform
```

**How to verify:**
```bash
python3 -c "exec(open('airflow/dags/weather_data_transformation.py').read()); print('✓ DAG defined')"
```

---

### 3. `dbt/myproject/models/staging/_stg_weather_data.yml` (NEW)
**Purpose:** Define schema for staging model  
**Contents:** Column definitions, data types, tests  
**Usage:** Enforces contract for `stg_weather_data` model  

**Key sections:**
```yaml
version: 2

models:
  - name: stg_weather_data
    config:
      contract:
        enforced: true  # Schema is now enforced
    columns:
      - name: id
        data_type: bigint
        tests:
          - unique
          - not_null
      - name: city
        data_type: varchar
        tests:
          - not_null
      # ... 18 more columns
```

**How to verify:**
```bash
cd dbt/myproject && dbt parse && echo "✓ Schema definition valid"
```

---

### 4. `dbt/myproject/models/staging/validate_raw_weather.sql` (NEW)
**Purpose:** Data quality validation query  
**Usage:** Can be called by Airflow before dbt run  
**Checks:** Null values, data ranges, freshness  

**Key validations:**
```sql
SELECT
    'data_quality_check' as check_name,
    COUNT(*) as total_records,
    COUNT(CASE WHEN city IS NULL THEN 1 END) as null_city,
    COUNT(CASE WHEN temperature < -50 OR temperature > 60 THEN 1 END) as invalid_temperature,
    -- ... more quality checks
FROM dev.raw_weather_data
WHERE inserted_at > NOW() - INTERVAL '2 hours'
```

**How to verify:**
```bash
cd dbt/myproject && dbt parse --select validate_raw_weather && echo "✓ Query valid"
```

---

## 📖 Documentation Created (3 files)

### 1. `RELIABILITY_AND_INTEGRITY_GUIDE.md` (12 KB)
**Comprehensive guide** covering:
- Architecture overview (before/after)
- Retry & timeout configuration details
- Schema validation implementation
- dbt contracts & tests
- Deployment & testing procedures
- Monitoring recommendations
- Rollback instructions
- FAQ

**Read when:** You want to understand the full implementation

---

### 2. `IMPLEMENTATION_CHECKLIST.md` (11 KB)
**Detailed verification checklist** with:
- Complete list of all changes
- Verification status for each component
- Configuration parameters reference table
- Deployment steps
- Rollback procedures
- Monitoring & alerting setup

**Read when:** During deployment or verification

---

### 3. `QUICK_START.md` (6 KB)
**Quick reference** with:
- 2-minute overview of changes
- Configuration at a glance
- Testing commands
- Q&A for common questions

**Read when:** You need the quick version

---

## 🔍 What Changed? Quick Reference

| Component | Before | After |
|-----------|--------|-------|
| **Retry Logic** | None | 3× ingest, 2× transform |
| **Timeout** | None | 30s DB ops, 10min ingest, 30min transform |
| **Schema Validation** | None | Spark validation + dbt contracts |
| **Data Freshness** | None | Warn 90 min, error 120 min |
| **DAGs** | 1 monolithic | 2 specialized |
| **Schedule** | Every 30 min | Every 1 hour (ingest) + 2 hours (transform) |
| **SLA** | None | 15 min (ingest), 45 min (transform) |

---

## 🚀 Deployment Checklist

### Phase 1: Verification (Before Deployment)
- [ ] Read QUICK_START.md (2 min)
- [ ] Verify Python syntax: `python3 -c "from api_request.insert_records import *"`
- [ ] Verify Airflow DAGs: `python3 airflow/dags/weather_data_ingestion.py`
- [ ] Verify dbt: `cd dbt/myproject && dbt parse`

### Phase 2: Deployment
- [ ] Copy `weather_data_ingestion.py` to `$AIRFLOW_HOME/dags/`
- [ ] Copy `weather_data_transformation.py` to `$AIRFLOW_HOME/dags/`
- [ ] Pause old DAG: `airflow dags pause weather_api_dbt_orchestrator`
- [ ] Wait for Airflow to pick up new DAGs (5-10 min)

### Phase 3: Testing
- [ ] Test ingest DAG: `airflow dags test weather_data_ingestion 2026-06-09`
- [ ] Check logs: `airflow logs weather_data_ingestion -1`
- [ ] Test transform DAG: `airflow dags test weather_data_transformation 2026-06-09`
- [ ] Run dbt tests: `cd dbt/myproject && dbt test`

### Phase 4: Monitoring
- [ ] Watch Airflow UI for first real run
- [ ] Check for any retries (should be rare)
- [ ] Verify SLA compliance (15 min ingest, 45 min transform)
- [ ] Confirm data quality checks pass

### Phase 5: Cleanup
- [ ] After 24 hours of successful runs, delete `orchestrator.py`
- [ ] Set up alerts for retry, SLA, freshness

---

## 🔧 Configuration Parameters

### Retry Configuration
```
insert_chunk():          3 retries, 5→10→20→60s backoff
Ingest DAG:              3 retries, 5 min backoff
Transform DAG:           2 retries, 10 min backoff
```

### Timeout Configuration
```
DB operations:           30 seconds
Ingest DAG task:         10 minutes (600s)
Transform DAG task:      30 minutes (1800s)
```

### SLA Configuration
```
Ingest DAG:              15 minutes (900s)
Transform DAG:           45 minutes (2700s)
```

### Data Freshness
```
Warning:                 90 minutes without new data
Error:                   120 minutes without new data
```

---

## 🔄 Rollback Instructions

If issues occur:

```bash
# Remove new DAGs
rm $AIRFLOW_HOME/dags/weather_data_ingestion.py
rm $AIRFLOW_HOME/dags/weather_data_transformation.py

# Restore old DAG
airflow dags unpause weather_api_dbt_orchestrator

# Revert insert_records.py (if needed)
git checkout HEAD -- api_request/insert_records.py

# Revert dbt changes (if needed)
git checkout HEAD -- dbt/myproject/models/
```

---

## 📞 Questions?

| Question | Answer Location |
|----------|-----------------|
| "What changed?" | QUICK_START.md |
| "How do I deploy?" | IMPLEMENTATION_CHECKLIST.md (Deployment section) |
| "How do I configure retries?" | RELIABILITY_AND_INTEGRITY_GUIDE.md (Configuration section) |
| "What do I monitor?" | IMPLEMENTATION_CHECKLIST.md (Monitoring section) |
| "How do I rollback?" | This file (Rollback section) |
| "Why exponential backoff?" | RELIABILITY_AND_INTEGRITY_GUIDE.md (FAQ) |

---

## ✅ Implementation Status

- ✅ All code written and verified
- ✅ All files created with proper syntax
- ✅ All configuration parameters set
- ✅ All documentation complete
- ✅ Ready for deployment

**Last Updated:** 2026-06-09  
**Version:** 1.0  
**Status:** ✅ COMPLETE
