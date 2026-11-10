-- Outcome metrics for AI-assisted work. One row per change (PR); one row per incident; one row per test per day.
-- Fill them from Forgejo webhooks, CI and the gateway's usage log (see the page). Matches the style of the Day 13 / capstone tables.
CREATE DATABASE IF NOT EXISTS ai;

CREATE TABLE IF NOT EXISTS ai.changes
(
    change_id        String,
    repo             LowCardinality(String),
    author_kind      LowCardinality(String),      -- 'human' | 'ai' | 'mixed'
    model_tier       LowCardinality(String),      -- 'frontier' | 'mid' | 'small' | '' for human
    first_commit_at  DateTime64(3, 'UTC'),
    opened_at        DateTime64(3, 'UTC'),
    first_review_at  Nullable(DateTime64(3, 'UTC')),
    merged_at        Nullable(DateTime64(3, 'UTC')),
    deployed_at      Nullable(DateTime64(3, 'UTC')),
    ci_first_pass    UInt8,                       -- 1 if the first CI run on the PR passed
    review_rounds    UInt16,
    reworked         UInt8,                       -- 1 if a follow-up fix landed within 7 days touching the same lines
    escaped_defect   UInt8,                       -- 1 if linked to a production incident or revert
    caused_failure   UInt8,                       -- 1 if the deploy needed rollback/hotfix (change failure rate)
    cost_usd         Float64,                     -- gateway spend attributed to this change
    tokens           UInt64,                      -- keep it; just never report it as an achievement
    coverage_delta   Float32,                     -- percentage points
    mutation_delta   Float32
)
ENGINE = MergeTree ORDER BY (repo, opened_at);

CREATE TABLE IF NOT EXISTS ai.incidents
(
    incident_id   String,
    repo          LowCardinality(String),
    opened_at     DateTime64(3, 'UTC'),
    resolved_at   Nullable(DateTime64(3, 'UTC')),
    resolved_by   LowCardinality(String)           -- 'human' | 'ai-assisted'
)
ENGINE = MergeTree ORDER BY (repo, opened_at);

CREATE TABLE IF NOT EXISTS ai.test_runs
(
    day        Date,
    test_id    String,
    runs       UInt32,
    flaky_runs UInt32                               -- failed then passed on retry with no code change
)
ENGINE = MergeTree ORDER BY (day, test_id);
