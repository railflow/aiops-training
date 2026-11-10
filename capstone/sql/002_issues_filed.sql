-- Every issue an agent filed, with the fingerprint used to dedupe it. Which planted bug (if any) it matches is decided LATER, outside the agent's pod, and
-- recorded in capstone.issue_matches: the answer key never enters the sandbox.
CREATE TABLE IF NOT EXISTS capstone.issues_filed
(
    ts              DateTime64(3, 'UTC')    DEFAULT now64(3),
    repo            LowCardinality(String),
    issue_number    UInt32,
    fingerprint     String                  COMMENT 'sha256 of repo + file + test name + normalised message',
    title           String,
    severity        LowCardinality(String),
    category        LowCardinality(String)  DEFAULT '',
    agent_run_id    String,
    failing_test    String                  DEFAULT '',
    file            String                  DEFAULT '',
    line            UInt32                  DEFAULT 0,
    state           LowCardinality(String)  DEFAULT 'open'
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(ts)
ORDER BY (repo, fingerprint)
TTL toDateTime(ts) + INTERVAL 2 YEAR;

CREATE TABLE IF NOT EXISTS capstone.issue_matches
(
    ts            DateTime64(3, 'UTC')    DEFAULT now64(3),
    repo          LowCardinality(String),
    issue_number  UInt32,
    planted_id    String,
    rule          LowCardinality(String)  DEFAULT 'file+line' COMMENT 'how the match was made (gen/answer_key.py match)'
)
ENGINE = MergeTree
ORDER BY (repo, planted_id, issue_number);
