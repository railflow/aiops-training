# Consolidation exercise (Day 25)

1. `./before.sh apply`: three teams, three private Postgres servers (with a bad shared password).
2. `../inventory.sh`: see the duplication and the memory it costs.
3. Consolidate onto `../shared-services/` with `../platform db <name>`: one server, one database and role per app.
4. Move each team's data (dump and restore), switch the app to the new Secret, delete the old Deployment.
5. `./before.sh delete` when you are done.

The reference solution is `../shared-services/`. Try it yourself first, with an AI assistant if you like: that is the point.
