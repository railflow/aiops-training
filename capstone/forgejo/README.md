# forgejo/: 100 folders into Forgejo

`push_repos.py` and `push_repos.sh` do the same thing (pick the one your team can maintain). `ci.yaml` is the golden-path workflow they add. `cleanup.sh` deletes only the repos in the CSV.

Needs: `FORGEJO_URL`, `FORGEJO_TOKEN` (write:organization, write:repository, write:issue), optionally `WEBHOOK_SECRET`, `WEBHOOK_URL`. **Projects:** no API creates a project board (checked in a development swagger); the scripts flip `has_projects` on and create `status/*` labels as a board convention.
