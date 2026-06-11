# Data Reliability & Integrity Implementation Guide

## Overview
This document outlines the comprehensive enhancements made to the Weather ETL Pipeline for **data reliability** (retries, timeouts) and **data integrity** (schema validation, data quality checks).

---

## Architecture Changes

### Before: Single Monolithic DAG
```
weather_api_dbt_orchestrator (Every 30 min)
├── Task 1: Generate data + Transform + Insert
└── Task 2: dbt models (staging → intermediate → mart)
```

### After: Two Specialized DAGs
```
DAG 1: weather_data_ingestion (Every 1 hour)
└── Task: Generate raw data → Save to dev.raw_weather_data
   Reliability: 3 retries, 10-min timeout, 15-min SLA

DAG 2: weather_data_transformation (Every 2 hours)
├── Task 1: Validate dev.raw_weather_data
└── Task 2: dbt run (staging → intermediate → mart)
   Reliability: 2 retries, 30-min timeout, 45-min SLA
```

**Benefit:** Clear separation of concerns. If data generation fails, it doesn't block transformations. Transformations have more time due to higher complexity.

---

## Data Reliability Enhancements

### 1. Retry Strategy

#### `insert_records.py` - Exponential Backoff Decorator
```python
@retry_with_backoff(max_retries=3, base_delay=5)
def insert_chunk(conn_params, chunk, chunk_id, total):
    # Attempt 1: Fails after 5s
    # Attempt 2: Fails after 10s (2x backoff)
    # Attempt 3: Fails after 20s (2x backoff)
    # Attempt 4: Fails after 60s (capped)
```

**Configuration:**
- **Max retries:** 3 for ingestion (fast, low cost if it fails)
- **Backoff:** 5s, 10s, 20s, 60s (exponential with cap)
- **Applies to:** `insert_chunk()`, `connect_to_db()`, `create_table()`

#### Airflow DAG Retry Configuration
```python
default_args = {
    'retries': 3,  # Ingest DAG
    'retry_delay': timedelta(minutes=5),
}

default_args = {
    'retries': 2,  # Transform DAG
    'retry_delay': timedelta(minutes=10),
}
```

**Rationale:**
- Ingestion is lightweight, can retry quickly
- Transformation is complex, needs longer backoff
- Lower retry count for transform avoids cascading failures

### 2. Timeout Protection

#### DB Operations (insert_records.py)
```python
with timeout_context(operation="Insert weather records", timeout=30):
    cursor.executemany(insert_sql, rows)
    conn.commit()
```

**Configuration:**
- **DB operation timeout:** 30 seconds
- **Raises:** `TimeoutError` with operation context
- **Implementation:** Uses `signal.SIGALRM` (Unix-compatible)

#### Airflow Task Timeouts
```python
# Ingestion DAG
execution_timeout=timedelta(minutes=10)  # 600s

# Transformation DAG
execution_timeout=timedelta(minutes=30)  # 1800s
```

### 3. Structured Logging

All failures logged with context:
```
Retrying connect_to_db (attempt 2/3) after 10s: connection timeout
Timeout in Insert weather records operation
Validation failed: 15 records don't match schema
```

---

## Data Integrity Enhancements

### 1. Schema Validation (insert_records.py)

#### Spark Schema Definition
```python
WEATHER_SCHEMA = StructType([
    StructField("city", StringType(), True),
    StructField("temperature", FloatType(), True),
    StructField("weather_description", StringType(), True),
    # ... 18 more fields
])
```

#### Validation Function
```python
def validate_records(records, spark):
    """
    Pre-insertion validation:
    1. Schema matching (type coercion)
    2. Null checks on critical fields
    3. Range validation (temperature, humidity, etc.)
    """
    df = spark.createDataFrame(records, schema=WEATHER_SCHEMA)
    # Validation filters applied
    return validated_rows
```

**What's checked:**
- ✅ All fields match expected types
- ✅ Critical fields (city, temperature, time) are not null
- ✅ Invalid records are filtered/logged
- ✅ Schema mismatches raise `ValueError`

### 2. dbt Contracts & Tests

#### Source Configuration (sources.yml)
```yaml
sources:
  - name: dev
    tables:
      - name: raw_weather_data
        freshness:
          warn_after: {count: 90, period: minute}
          error_after: {count: 120, period: minute}
        columns:
          - name: id
            tests:
              - unique
              - not_null
          - name: city
            tests:
              - not_null
          - name: temperature
            tests:
              - not_null
          - name: weather_description
            tests:
              - accepted_values:
                  values: ['Clear', 'Cloudy', 'Rainy', ...]
```

**What's enforced:**
- ✅ Data freshness checks (warn at 90 min, error at 120 min)
- ✅ Unique ID constraint
- ✅ Non-null constraints on critical fields
- ✅ Valid weather descriptions

#### Staging Model Contract (_stg_weather_data.yml)
```yaml
models:
  - name: stg_weather_data
    config:
      contract:
        enforced: true
    columns:
      - name: id
        data_type: int
        constraints:
          - type: not_null
      - name: city
        data_type: text
        constraints:
          - type: not_null
      # ... 19 more columns
```

**Enforcement:**
- ✅ Columns must match exact schema
- ✅ Data types verified on each run
- ✅ Nullable constraints enforced
- ✅ Contract violations fail immediately

### 3. Data Quality SQL (validate_raw_weather.sql)

Pre-transformation validation query:
```sql
SELECT
    'data_quality_check' as check_name,
    COUNT(*) as total_records,
    COUNT(CASE WHEN city IS NULL THEN 1 END) as null_city,
    COUNT(CASE WHEN temperature IS NULL THEN 1 END) as null_temperature,
    COUNT(CASE WHEN temperature < -50 OR temperature > 60 THEN 1 END) as invalid_temperature,
    -- ... more validations
FROM dev.raw_weather_data
WHERE inserted_at > NOW() - INTERVAL '2 hours'
```

Can be used by Airflow validation task before running dbt:
```python
# In weather_data_transformation.py
def validate_raw_data():
    conn = psycopg2.connect(...)
    cursor = conn.cursor()
    cursor.execute(open('validate_raw_weather.sql').read())
    results = cursor.fetchall()
    # Check for any quality issues
    assert results[0]['null_city'] == 0, "Found null cities!"
```

---

## File Changes Summary

### Created Files

1. **airflow/dags/weather_data_ingestion.py** (2.9 KB)
   - DAG 1: Hourly raw data generation
   - Task: `ingest_data_task` (PythonOperator)
   - Retry: 3 attempts, 5-min backoff
   - Timeout: 10 minutes

2. **airflow/dags/weather_data_transformation.py** (5.6 KB)
   - DAG 2: 2-hourly transformation
   - Task 1: `validate_raw_data` (PythonOperator)
   - Task 2: `dbt_transform` (DockerOperator)
   - Retry: 2 attempts, 10-min backoff
   - Timeout: 30 minutes

3. **dbt/myproject/models/staging/_stg_weather_data.yml** (2.7 KB)
   - Schema definition for staging model
   - Data quality tests
   - Column constraints

4. **dbt/myproject/models/staging/validate_raw_weather.sql** (1.9 KB)
   - Data quality validation query
   - Can be called by Airflow before dbt

### Modified Files

1. **api_request/insert_records.py**
   - Added `@retry_with_backoff()` decorator
   - Added `timeout_context()` manager
   - Added `validate_records()` function
   - Updated `insert_chunk()` with retry logic
   - Enhanced error logging

2. **dbt/myproject/models/sources/sources.yml**
   - Added freshness assertions
   - Added column tests (unique, not_null)
   - Added accepted_values test for weather_description

3. **dbt/myproject/models/staging/stg_weather_data.sql**
   - Added contract enforcement
   - No changes to SQL logic (backward compatible)

### Preserved Files

- **airflow/dags/orchestrator.py** — Kept for rollback/reference (can be deleted after validation)
- **dbt/myproject/models/intermediate/silver_weather_data.sql** — No changes
- **dbt/myproject/models/mart/*.sql** — No changes

---

## Configuration Parameters

### Retry & Timeout Configuration

| Component | Retries | Backoff | Timeout | SLA |
|-----------|---------|---------|---------|-----|
| insert_records.py (decorator) | 3 | 5-60s exp | 30s (DB ops) | N/A |
| DAG 1: Ingestion | 3 | 5 min | 10 min | 15 min |
| DAG 2: Transform | 2 | 10 min | 30 min | 45 min |

### Freshness Thresholds

```yaml
freshness:
  warn_after: 90 minutes
  error_after: 120 minutes
```

If `dev.raw_weather_data` hasn't received new data in 90 minutes, dbt warns. If no data in 120 minutes, dbt errors.

### Data Validation Rules

**Ingestion validations (insert_records.py):**
- ✅ All fields match Spark schema
- ✅ city IS NOT NULL
- ✅ temperature IS NOT NULL
- ✅ time IS NOT NULL
- ✅ weather_severity >= 1

**dbt validations (sources.yml + contracts):**
- ✅ id is unique and not null
- ✅ city, temperature, weather_severity, time NOT NULL
- ✅ weather_description is one of 21 valid types
- ✅ Data freshness within 2 hours

---

## Deployment & Testing

### Pre-deployment Checklist

```bash
# 1. Verify Python syntax
python -m py_compile airflow/dags/weather_data_ingestion.py
python -m py_compile airflow/dags/weather_data_transformation.py
python -m py_compile api_request/insert_records.py

# 2. Verify dbt YAML syntax
dbt parse --project-dir dbt/myproject

# 3. Verify dbt models
dbt run --project-dir dbt/myproject --select stg_weather_data

# 4. Test retry decorator
python -c "from api_request.insert_records import *; print('Import OK')"
```

### Testing Each DAG

```bash
# Test Ingestion DAG
airflow dags test weather_data_ingestion 2026-06-09

# Test Transformation DAG
airflow dags test weather_data_transformation 2026-06-09

# Test dbt models
dbt test --project-dir dbt/myproject
```

### Monitoring After Deployment

**Watch for in Airflow UI:**
- Task retry attempts logged in task logs
- SLA violations tracked per DAG
- Timeout exceptions with operation context

**Watch in dbt:**
- Freshness check status in `manifest.json`
- Contract violations in logs
- Test failures in dbt reports

---

## Rollback Plan

If issues occur:

### Step 1: Revert to old DAG
```bash
# Delete new DAGs
rm airflow/dags/weather_data_ingestion.py
rm airflow/dags/weather_data_transformation.py

# Unpause old DAG
airflow dags unpause weather_api_dbt_orchestrator
```

### Step 2: Revert insert_records.py (if retry causes issues)
```bash
git checkout HEAD -- api_request/insert_records.py
```

### Step 3: Revert dbt models (if contracts cause issues)
```bash
git checkout HEAD -- dbt/myproject/models/sources/sources.yml
git checkout HEAD -- dbt/myproject/models/staging/stg_weather_data.sql
rm dbt/myproject/models/staging/_stg_weather_data.yml
```

---

## FAQ

**Q: Why 3 retries for ingest but 2 for transform?**  
A: Ingestion is fast and cheap (5-10s). If it fails, retrying quickly is low-risk. Transformation is slow (20-30min), so fewer retries avoid tying up resources.

**Q: What if insert_chunk retries 3x but dbt also retries?**  
A: Good question! The data will sit in `dev.raw_weather_data`. The transform DAG will pick it up on the next run (every 2 hours). This is fine—dbt is idempotent.

**Q: Can I adjust timeout values?**  
A: Yes! Edit:
- DB timeout: `timeout_context(..., timeout=30)` in insert_records.py
- Airflow timeout: `execution_timeout=timedelta(minutes=X)` in DAG files

**Q: What happens if validation fails?**  
A: 
- insert_records.py: Records fail validation and are logged, task continues
- dbt: dbt test failures block downstream models

**Q: How do I monitor this in production?**  
A: Use Airflow logs, dbt metrics, and Postgres query logs. Set up alerts for:
- SLA violations (>15min ingestion, >45min transform)
- Task retries (repeated failures)
- Freshness breaches (>120min without data)

---

## Next Steps

1. **Deploy to Airflow:** Copy DAG files to airflow/dags/
2. **Run dbt compile:** `dbt compile --project-dir dbt/myproject`
3. **Run dbt tests:** `dbt test --project-dir dbt/myproject`
4. **Monitor first run:** Watch ingestion DAG at :00, transformation at :00 of even hours
5. **Remove old DAG:** After 1-2 successful cycles, delete orchestrator.py

---

**Questions?** See plan.md or implementation details in individual files.
