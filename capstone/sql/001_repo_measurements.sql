-- One immutable row per measurement of one repo at one commit. Improvement over time is a query, never an UPDATE.
-- Written for ClickHouse 24.8 (the course's version); also run against an embedded ClickHouse in the tests.
CREATE DATABASE IF NOT EXISTS capstone;

CREATE TABLE IF NOT EXISTS capstone.repo_measurements
(
    ts                  DateTime64(3, 'UTC')        DEFAULT now64(3),
    repo                LowCardinality(String),
    language            LowCardinality(String),
    commit_sha          String,
    run_id              String                      COMMENT 'one measure run (a CI run, a Job, a Temporal activity)',
    agent_run_id        String                      DEFAULT '' COMMENT 'set when the commit came from an agent run',
    iteration           UInt16                      DEFAULT 0 COMMENT '0 = baseline',
    lines_of_code       UInt32,
    files               UInt32,
    test_count          UInt32,
    tests_passed        UInt32,
    tests_failed        UInt32,
    line_coverage_pct   Nullable(Float32),
    branch_coverage_pct Nullable(Float32),
    vuln_critical       Nullable(UInt32),
    vuln_high           Nullable(UInt32),
    vuln_medium         Nullable(UInt32),
    vuln_low            Nullable(UInt32),
    secrets_found       Nullable(UInt32),
    lint_issues         Nullable(UInt32),
    complexity_avg      Nullable(Float32),
    build_ok            UInt8,
    test_duration_s     Nullable(Float32),
    planted_issues_found UInt32                     DEFAULT 0,
    planted_issues_fixed UInt32                     DEFAULT 0,
    source              LowCardinality(String)      DEFAULT 'measure.py' COMMENT 'which tool wrote the row'
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(ts)
ORDER BY (repo, ts)
TTL toDateTime(ts) + INTERVAL 2 YEAR
COMMENT 'Course capstone: immutable per-commit repo measurements';
