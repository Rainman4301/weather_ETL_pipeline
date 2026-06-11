# Data Integrity Enhancements for Weather ETL Pipeline

## Overview
This document describes the data integrity enhancements made to the dbt models in the Weather ETL Pipeline, focusing on data quality, freshness checks, and schema contracts.

## 1. Source Layer Enhancements (`models/sources/sources.yml`)

### Freshness Assertions
The `raw_weather_data` source now includes automated freshness checks:
- **Warning**: Data is considered stale after 90 minutes
- **Error**: Data is considered outdated after 120 minutes
- **Loaded At Field**: `inserted_at` (timestamp when ETL inserted the record)

These checks ensure that the ETL pipeline is running on schedule and data is arriving regularly.

### Data Quality Tests
Tests are now defined for critical columns to catch data quality issues early:

| Column | Tests | Purpose |
|--------|-------|---------|
| `id` | unique, not_null | Ensures each record is unique and identifiable |
| `city` | not_null | City must always be present |
| `temperature` | not_null | Temperature readings are required |
| `weather_severity` | not_null | Severity scores must be recorded |
| `time` | not_null | Timestamp must exist for all records |
| `weather_description` | accepted_values | Only valid weather conditions allowed |

## 2. Staging Layer Enhancements (`models/staging/stg_weather_data.sql`)

### Contract Enforcement
The staging model now includes dbt contract enforcement:
```jinja2
{{ config(
    materialized='incremental',
    unique_key='id',
    post_hook="DELETE FROM {{ this }} WHERE inserted_at < NOW() - INTERVAL '30 days'",
    contract={"enforced": true}
) }}
```

**Benefits:**
- Output schema is validated against defined column specifications
- Build fails if actual output doesn't match contract
- Prevents silent breaking changes to downstream models
- Provides explicit documentation of expected output structure

### Maintained Features
- **Materialization**: Incremental (unchanged)
- **Unique Key**: `id` column
- **Cleanup**: Deletes records older than 30 days
- **Logic**: No changes to transformation logic

## 3. Staging Model YAML (`models/staging/_stg_weather_data.yml`)

### Column Definitions
All 20 columns in the staging model are now explicitly defined with:
- Data types (bigint, varchar, numeric, timestamp, boolean)
- Descriptions
- Data quality tests
- Constraints

### Column Tests
Critical columns include data quality tests:
- `id`: unique, not_null
- `city`: not_null
- `temperature`: not_null
- `weather_severity`: not_null
- `time`: not_null
- `weather_description`: accepted_values (21 valid weather types)

### Model Configuration
- **Contract Enforcement**: Enabled at model level
- **Schema Validation**: Ensures all columns match definitions
- **Data Type Validation**: Type mismatches will cause failures

## 4. Validation Query (`models/staging/validate_raw_weather.sql`)

### Purpose
Standalone SQL query that can be run before dbt execution to validate raw data quality. Useful for Airflow integration.

### Validations Performed

#### Null Checks
- Counts null values in critical fields: id, city, temperature, weather_severity, time, is_forecast

#### Range Validations
- **Temperature**: -60 to 60°C (physical limits)
- **Weather Severity**: 0 to 10 (severity score range)
- **Humidity**: 0 to 100% (percentage)
- **Pressure**: 870-1085 hPa (typical atmospheric range)
- **Cloud Cover**: 0-100% (percentage)
- **Precipitation Probability**: 0-100% (percentage)

#### Freshness Status
- Compares `inserted_at` against freshness thresholds
- Returns status: ERROR (>120 min), WARN (>90 min), or OK

### Usage
```sql
-- Run before dbt execution in Airflow
SELECT * FROM {{ ref('validate_raw_weather') }};

-- Review results for:
-- - null_*_count columns (should be 0)
-- - invalid_*_count columns (should be 0)
-- - freshness_status (should be 'OK')
```

## Testing Strategy

### Running Tests
```bash
# Run all tests
dbt test

# Run freshness checks
dbt source freshness

# Run only staging model tests
dbt test --select stg_weather_data

# Run specific test
dbt test --select stg_weather_data.not_null_stg_weather_data_id
```

### Test Failures
- **Freshness Errors**: Check ETL pipeline scheduling
- **Null Value Tests**: Investigate source data quality
- **Accepted Values**: Validate weather_description values in source
- **Unique Tests**: Check for duplicate records

## Backward Compatibility

✓ **No Breaking Changes**
- Existing transformation logic unchanged
- Model materialization unchanged
- Existing downstream dependencies unaffected
- New tests are non-blocking (can be marked as warnings)

## Future Enhancements

1. **Additional Range Tests**: Use dbt_expectations for complex validations
2. **Custom Macros**: Add weather-specific validation rules
3. **Test Documentation**: Document expected data distributions
4. **Alerting**: Integrate with dbt Cloud/Slack for test failure notifications
5. **Data Profiling**: Add tests for data distribution and outliers

## Deployment Notes

1. **First Deployment**: 
   - Run `dbt debug` to ensure connection works
   - Run `dbt parse` to validate all YAML
   - Run `dbt test` to establish baseline

2. **Ongoing**:
   - Schedule `dbt source freshness` checks in orchestration
   - Monitor test failure rates
   - Adjust severity levels based on business requirements

3. **Integration with Airflow**:
   - Use `validate_raw_weather.sql` in pre-dbt task
   - Parse freshness status in data quality checks
   - Fail Airflow task if validation returns errors

## References

- [dbt Contracts](https://docs.getdbt.com/docs/build/contracts)
- [dbt Freshness Checks](https://docs.getdbt.com/docs/build/sources#freshness-checks)
- [dbt Built-in Tests](https://docs.getdbt.com/docs/build/built-in-tests)
