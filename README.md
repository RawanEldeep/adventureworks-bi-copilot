# Business Intelligence Copilot

A natural-language business intelligence agent that answers questions over a relational database using Large Language Models (LLMs) and Knowledge Graphs (KGs). The retrieved context is passed to the LLM to generate accurate SQL queries answering the user's question.

## Database

This project uses the AdventureWorks database, Microsoft's official sample enterprise database, served via Docker using the `chriseaton/adventureworks:postgres` image.

Schemas of interest: `"Sales"`, `"Person"`, `"Production"`, `"Purchasing"`, `"HumanResources"`. Schema and table names are case-sensitive in Postgres and must be double-quoted in SQL, e.g. `"Sales"."SalesOrderHeader"`.

## Setup

1. `copy .env.example .env` and fill in real values
2. `docker compose up -d`
3. Create a virtual environment and install dependencies:
   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
4. `python src\main.py`

## Known setup gotchas

### "password authentication failed for user postgres" despite a correct `.env`

If `docker exec -it adventureworks-db psql -U postgres` connects **without** prompting for a password, but the same credentials fail from a Python/psql client on the host, you're likely hitting one or both of the issues below.

**1. `POSTGRES_PASSWORD` is silently ignored on this image.**

`chriseaton/adventureworks:postgres` ships with a pre-baked data directory already containing an initialized database. Postgres only applies `POSTGRES_PASSWORD` during `initdb` on a *first-time, empty* data directory — since this image's data directory (and the named volume `adventureworks_data` after first run) is never empty, the env var in `docker-compose.yml` has no effect on the actual `postgres` role password. You can confirm this by checking the container logs:

```
docker logs adventureworks-db
```

Look for: `PostgreSQL Database directory appears to contain a database; Skipping initialization`. If you see that line, `POSTGRES_PASSWORD` was never applied.

**Fix** — set the password explicitly against the running container, using the trust-authenticated local connection:

```
docker exec -i adventureworks-db psql -U postgres -c "ALTER USER postgres WITH PASSWORD 'yourpassword';"
```

This persists in the named volume, so you only need to do it once (unless the volume is deleted).

**2. A native PostgreSQL install on the host may be squatting port 5432.**

If you have PostgreSQL installed natively on Windows (e.g. as a service, `postgresql-x64-17`), it can also bind `localhost:5432`. Depending on which listener the OS routes to, your client may connect to the *native* Postgres instance instead of the Dockerized one — which has a completely different, unknown password, producing the exact same auth error even after fixing #1.

Check for a conflicting listener:

```
netstat -ano | findstr :5432
```

If more than one PID is listening on `5432`, you have a conflict. Rather than stopping a system service that may be used elsewhere, this project maps the container to host port **5433** instead (see `docker-compose.yml` — `"5433:5432"` — and `.env.example` — `DB_PORT=5433`). Recreate the container after changing the port mapping:

```
docker compose down
docker compose up -d
```

### Segfault when running scripts that use `pandas.read_sql`

`pandas==2.2.2` predates official Python 3.13 support and can segfault when paired with a newer `numpy` on Python 3.13 (`Segmentation fault` / exit code 139, no traceback). If you're on Python 3.13, upgrade pandas:

```
pip install -U pandas
```

`requirements.txt` is pinned to a version confirmed working on Python 3.13 (`pandas==3.0.5`). If you're on an older Python, `pandas==2.2.2` is fine.

## Collaborators

Repo access for `ykhadragy01` and `iTasneem` needs to be granted manually on github.com under **Settings > Collaborators** — this cannot be done via CLI.
