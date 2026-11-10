-- One row per agent Job: what it cost and how it ended. Cost per coverage point is a join of this with repo_measurements.
CREATE TABLE IF NOT EXISTS capstone.agent_runs
(
    ts              DateTime64(3, 'UTC')    DEFAULT now64(3),
    agent_run_id    String,
    repo            LowCardinality(String),
    iteration       UInt16,
    model           LowCardinality(String)  COMMENT 'whatever model name you configured, recorded and never assumed',
    prompt_version  LowCardinality(String),
    tool_versions   String                  DEFAULT '' COMMENT 'for example claude-code and build.sh versions',
    tokens_in       UInt64                  DEFAULT 0,
    tokens_out      UInt64                  DEFAULT 0,
    cost_usd        Float32                 DEFAULT 0,
    duration_s      Float32,
    commits         UInt16                  DEFAULT 0,
    tests_added     UInt32                  DEFAULT 0,
    issues_filed    UInt16                  DEFAULT 0,
    outcome         LowCardinality(String)  COMMENT 'ok | no_change | rejected_by_integrity | budget_exceeded | timeout | error'
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(ts)
ORDER BY (repo, ts)
TTL toDateTime(ts) + INTERVAL 2 YEAR;
