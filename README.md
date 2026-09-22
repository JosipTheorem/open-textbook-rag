# Open Textbook RAG Lab

A local-first study platform for turning openly licensed or user-authorized
technical textbooks into grounded AI learning companions.

## Local database

Docker runs PostgreSQL with pgvector plus a private CPU-only Ollama service for
embeddings. Original and processed textbook files stay in the ignored `data/`
folders. Build and start the services from the repository root:

```powershell
docker compose up -d --build
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

## Embeddings and hybrid search

Download the embedding model once on each computer. Its files remain in a
Docker volume and are not committed to Git:

```powershell
docker compose exec ollama-embeddings ollama pull qwen3-embedding:0.6b
```

After importing textbook chunks and applying all migrations, generate every
missing embedding in DBeaver:

```sql
CALL textbook.embed_chunks();
```

The embedding service runs on the CPU so the RTX GPU remains available for the
local LLM. Search needs only the question and desired result count:

```sql
SELECT *
FROM textbook.search_chunks_hybrid('What is machine learning?', 5);
```

See `database/embed_and_search.sql` for checks and readable examples.

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

## Import a licensed textbook sample

The first source is the official Git repository for *Dive into Deep Learning*,
licensed under CC BY-SA 4.0. Import one Introduction document from the approved
source manifest:

```powershell
.\.venv\Scripts\python.exe .\scripts\ingest_book.py `
    https://github.com/d2l-ai/d2l-en `
    --max-files 1
```

The importer records the exact Git revision and license, preserves the heading
hierarchy, stores paragraphs/code/equations as typed blocks, and creates chunks
that never cross section boundaries. Re-running the same revision replaces its
structured content instead of duplicating it. Downloaded source files remain in
ignored `data/raw/` storage.

This stage deliberately leaves `textbook.chunks.embedding` empty. Run
`CALL textbook.embed_chunks();` after inspecting the imported chunks.

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
