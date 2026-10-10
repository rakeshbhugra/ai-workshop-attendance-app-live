# Database health and container startup

`/health` reports process liveness without contacting the database.
`/health/ready` executes `SELECT 1` against the configured database and returns
200 with `{"status":"ready","database":"up"}` or 503 with
`{"status":"unavailable","database":"down"}`. Connection acquisition and
the query share a two-second timeout by default.

Both container images wait for the database before running migrations, then
start the server only after migrations succeed. This also works when launching
the images without Compose, including against an external database. A database
that stays unavailable causes startup to exit with status 1 after 60 seconds;
migrations and the server are skipped. Compose additionally waits for its
PostgreSQL service health check.

Configure the wait using `ATTENDANCE_DB_STARTUP_TIMEOUT_SECONDS` (default 60)
and `ATTENDANCE_DB_STARTUP_RETRY_SECONDS` (default 1). Both Compose stacks pass
these settings from the environment or `.env`. Direct Python launches can set
`ATTENDANCE_DB_PROBE_TIMEOUT_SECONDS` (default 2) as well. All three values must
be positive. Keep the probe timeout below the HTTP/container probe deadlines.

Container health checks use `/health/ready`. Docker reports a running container
as unhealthy during a database outage; Docker's restart policy alone does not
restart unhealthy containers. The next successful probe restores health.
Server liveness remains available at `/health` during an outage.

For local startup outside Docker, use `python -m attendance.wait_for_database`
before `alembic upgrade head` and your server command. The wait checks database
connectivity, not schema currency; Alembic remains responsible for migrations.
