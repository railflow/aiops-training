# measure/: baseline measurement

- `measure.py`: detect language, run tests with coverage, print one JSON document (a `capstone.repo_measurements` row). Exit 0 whenever it produced a document.
- `ship.py`: INSERT JSON rows into ClickHouse over HTTP (stdlib only). Also `query_rows` for SELECTs.
- `build.sh measure` (in `tools/`) wraps both; `MEASURE_SHIP=1` ships.
- `Dockerfile`: builder image + cloc + .NET SDK. `baseline-job.yaml` + `baseline.sh`: the Indexed Job.
- Tools: cloc (optional), JaCoCo (Java), `go test -coverprofile` (Go), pytest-cov (Python), `node --test --experimental-test-coverage` (Node 22), coverlet via `dotnet test --collect` (.NET), `trivy fs` (vulnerabilities and secrets, optional).
