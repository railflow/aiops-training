# sql/

Apply in order against ClickHouse (`001` creates the `capstone` database). `queries.sql` has named queries, one per dashboard panel idea; `../tests/test_sql.py` runs them all on seeded rows.
Apply to the course ClickHouse: `kubectl -n observability exec -i deploy/clickhouse -- clickhouse-client --user default --multiquery < 001_repo_measurements.sql` (check user and password for your install).
