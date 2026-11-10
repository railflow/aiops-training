-- The answer key: one row per planted bug, loaded from the answer-key files (gen/answer_key.py load).
CREATE TABLE IF NOT EXISTS capstone.planted_issues
(
    repo        LowCardinality(String),
    planted_id  String,
    file        String,
    line_start  UInt32,
    line_end    UInt32,
    category    LowCardinality(String),
    severity    LowCardinality(String),
    description String
)
ENGINE = MergeTree
ORDER BY (repo, planted_id);
