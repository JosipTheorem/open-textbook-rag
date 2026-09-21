# Open Textbook RAG Lab

A local-first study platform for turning openly licensed or user-authorized
technical textbooks into grounded AI learning companions.

## Local database

Docker runs PostgreSQL with pgvector for organized and searchable textbook data.
Original and processed textbook files stay in the ignored `data/` folders. Start
the database from the repository root:

```powershell
docker compose up -d
```

The first start downloads the container image and can take a few minutes. Check
its status:

```powershell
docker compose ps
```

The default local database settings are documented in `.env.example`. To use
your own settings, copy `.env.example` to `.env` and edit the copy before
starting the database. Git ignores `.env`.

Stop the services without deleting their data:

```powershell
docker compose down
```

Start it again with `docker compose up -d`; database data is kept in a named
Docker volume.

## Database versions

Alembic records database-structure changes in Git. Apply every migration that
has not yet run on the current computer:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Check the installed database version:

```powershell
.\.venv\Scripts\python.exe -m alembic current
```

The authoritative history is in `migrations/versions/`. The generated
`database/schema.sql` file provides the equivalent readable PostgreSQL DDL and
must not be edited manually.

## Project board

Run the local visual project board from the repository root:

```powershell
.\.venv\Scripts\python.exe .\project_board\run_board.py
```

The board opens automatically at:

```text
http://127.0.0.1:8765/project_board/
```

Task changes are saved to `project_board/tasks.json`, so they can be committed
and synchronized through Git. Stop the server with `Ctrl+C`.
