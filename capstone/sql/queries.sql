-- Name: baseline_vs_latest   one row per repo: first and latest coverage and the gain
WITH ranked AS (
  SELECT repo, line_coverage_pct, ts,
         row_number() OVER (PARTITION BY repo ORDER BY ts ASC)  AS first_rn,
         row_number() OVER (PARTITION BY repo ORDER BY ts DESC) AS last_rn
  FROM capstone.repo_measurements
  WHERE line_coverage_pct IS NOT NULL
)
SELECT repo,
       maxIf(line_coverage_pct, first_rn = 1) AS baseline_pct,
       maxIf(line_coverage_pct, last_rn  = 1) AS latest_pct,
       latest_pct - baseline_pct              AS gain_pct
FROM ranked GROUP BY repo ORDER BY gain_pct DESC;

-- Name: fleet_average_coverage_over_time   daily fleet average of each repo's latest value that day
SELECT toDate(ts) AS day, round(avg(line_coverage_pct), 1) AS avg_line_coverage
FROM (SELECT repo, ts, line_coverage_pct, row_number() OVER (PARTITION BY repo, toDate(ts) ORDER BY ts DESC) AS rn
      FROM capstone.repo_measurements WHERE line_coverage_pct IS NOT NULL)
WHERE rn = 1 GROUP BY day ORDER BY day;

-- Name: worst_repos   leaderboard of the lowest current coverage
SELECT repo, any(language) AS language, argMax(line_coverage_pct, ts) AS coverage, argMax(lines_of_code, ts) AS loc,
       argMax(vuln_critical, ts) AS critical, argMax(vuln_high, ts) AS high
FROM capstone.repo_measurements GROUP BY repo ORDER BY coverage ASC NULLS FIRST LIMIT 20;

-- Name: portfolio_totals   current totals across the fleet (latest row per repo)
SELECT count() AS repos, sum(loc) AS total_loc, round(avg(cov), 1) AS avg_coverage, sum(crit) AS critical, sum(high) AS high
FROM (SELECT repo, argMax(lines_of_code, ts) AS loc, argMax(line_coverage_pct, ts) AS cov,
             argMax(vuln_critical, ts) AS crit, argMax(vuln_high, ts) AS high
      FROM capstone.repo_measurements GROUP BY repo);

-- Name: repos_by_language
SELECT language, count() AS repos, round(avg(cov), 1) AS avg_coverage
FROM (SELECT repo, any(language) AS language, argMax(line_coverage_pct, ts) AS cov FROM capstone.repo_measurements GROUP BY repo)
GROUP BY language ORDER BY repos DESC;

-- Name: stuck_repos   at least 3 measurements since the baseline and no coverage gain across the last 3
SELECT repo, count() AS measurements,
       arraySlice(groupArray(line_coverage_pct), -3) AS last_three
FROM (SELECT repo, ts, line_coverage_pct FROM capstone.repo_measurements WHERE iteration > 0 ORDER BY repo, ts)
GROUP BY repo
HAVING measurements >= 3 AND arrayMax(last_three) - arrayMin(last_three) < 0.5;

-- Name: planted_bug_recall   share of planted bugs that agents found, and precision of the issues filed
SELECT
  (SELECT count() FROM capstone.planted_issues)                                            AS planted_total,
  (SELECT uniqExact(repo, planted_id) FROM capstone.issue_matches)                           AS planted_found,
  round(100 * planted_found / planted_total, 1)                                            AS recall_pct,
  (SELECT uniqExact(repo, issue_number) FROM capstone.issues_filed)                          AS issues_filed,
  (SELECT uniqExact(repo, issue_number) FROM capstone.issue_matches)                         AS issues_matching_planted,
  round(100 * issues_matching_planted / nullIf(issues_filed, 0), 1)                        AS precision_pct;

-- Name: cost_per_coverage_point   dollars per percentage point gained, per repo
SELECT a.repo, round(sum(a.cost_usd), 2) AS cost_usd, any(g.gain) AS gain_pct,
       round(sum(a.cost_usd) / nullIf(any(g.gain), 0), 2) AS usd_per_point
FROM capstone.agent_runs AS a
LEFT JOIN (SELECT repo, argMax(line_coverage_pct, ts) - argMinIf(line_coverage_pct, ts, iteration = 0) AS gain
           FROM capstone.repo_measurements WHERE line_coverage_pct IS NOT NULL GROUP BY repo) AS g ON g.repo = a.repo
GROUP BY a.repo ORDER BY usd_per_point DESC;
