-- name: lead_time_hours_by_author
SELECT author_kind,
       count() AS merged,
       round(quantile(0.5)(dateDiff('minute', first_commit_at, merged_at)) / 60, 2) AS median_lead_h,
       round(quantile(0.9)(dateDiff('minute', first_commit_at, merged_at)) / 60, 2) AS p90_lead_h
FROM ai.changes WHERE merged_at IS NOT NULL GROUP BY author_kind ORDER BY author_kind;

-- name: review_turnaround_hours_by_author
SELECT author_kind, round(quantile(0.5)(dateDiff('minute', opened_at, first_review_at)) / 60, 2) AS median_first_review_h
FROM ai.changes WHERE first_review_at IS NOT NULL GROUP BY author_kind ORDER BY author_kind;

-- name: quality_by_author
SELECT author_kind,
       count() AS changes,
       round(avg(ci_first_pass) * 100, 1) AS ci_first_pass_pct,
       round(avg(reworked) * 100, 1) AS rework_pct,
       round(avg(escaped_defect) * 100, 1) AS escaped_defect_pct,
       round(avg(caused_failure) * 100, 1) AS change_failure_pct,
       round(avg(coverage_delta), 2) AS avg_coverage_delta_pp,
       round(avg(mutation_delta), 2) AS avg_mutation_delta_pp
FROM ai.changes GROUP BY author_kind ORDER BY author_kind;

-- name: cost_per_accepted_change
SELECT model_tier,
       count() AS merged,
       round(sum(cost_usd), 4) AS spend_usd,
       round(sum(cost_usd) / count(), 4) AS usd_per_merged_change,
       round(sum(cost_usd) / nullIf(countIf(reworked = 0 AND escaped_defect = 0), 0), 4) AS usd_per_clean_change
FROM ai.changes WHERE author_kind = 'ai' AND merged_at IS NOT NULL GROUP BY model_tier ORDER BY model_tier;

-- name: tokens_vs_outcomes
-- The Goodhart check: do the people (repos) who burn the most tokens ship better outcomes? Usually the answer is "no relationship", and that is the point.
SELECT repo, sum(tokens) AS tokens, count() AS changes, round(avg(ci_first_pass) * 100, 1) AS ci_first_pass_pct, round(avg(escaped_defect) * 100, 1) AS escaped_pct
FROM ai.changes GROUP BY repo ORDER BY tokens DESC;

-- name: time_to_resolve_hours
SELECT resolved_by, count() AS incidents, round(quantile(0.5)(dateDiff('minute', opened_at, resolved_at)) / 60, 2) AS median_ttr_h
FROM ai.incidents WHERE resolved_at IS NOT NULL GROUP BY resolved_by ORDER BY resolved_by;

-- name: flaky_rate
SELECT day, round(sum(flaky_runs) / sum(runs) * 100, 2) AS flaky_pct FROM ai.test_runs GROUP BY day ORDER BY day;
