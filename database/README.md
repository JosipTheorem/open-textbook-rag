# Database definition

Alembic migrations in `migrations/versions/` are the authoritative history of
the database structure. `schema.sql` is generated from that history so the
resulting PostgreSQL DDL can be inspected without reading Python.

Do not edit `schema.sql` manually. Regenerate it from the repository root with:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head --sql |
    Set-Content -Encoding utf8 .\database\schema.sql
```

Commit both the migration and the updated DDL together.

## SQL-driven embeddings and hybrid search

Migration `0003_embedding_search` configures normalized 1024-dimensional
embeddings from `qwen3-embedding:0.6b`, a cosine HNSW index, and one search
function: `textbook.search_chunks_hybrid`.

PostgreSQL cannot execute a transformer model by itself. The project therefore
uses the `http` PostgreSQL extension to call a private Ollama service on the
Docker network. That Ollama service is deliberately CPU-only, leaving the GPU
available for the answer-generating local LLM. It is not published to the host
or local network.

From the repository root, build and start the services:

```powershell
docker compose up -d --build
```

Download the embedding model into its persistent Docker volume. This is a
one-time command on each computer:

```powershell
docker compose exec ollama-embeddings ollama pull qwen3-embedding:0.6b
```

Apply the database migration:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Then open `database/embed_and_search.sql` in DBeaver. Its main embedding command
is ordinary SQL and may safely be rerun:

```sql
CALL textbook.embed_chunks();
```

It skips already embedded chunks. To search, only question text is required:

```sql
SELECT *
FROM textbook.search_chunks_hybrid('What is machine learning?', 5);
```

The function sends the question to the same embedding model, runs PostgreSQL
full-text and cosine-vector searches, and combines their ranks with reciprocal
rank fusion. Documents are embedded without a prefix; questions receive Qwen's
retrieval instruction. Ollama returns L2-normalized vectors.

The model files and database contents live in Docker volumes. Git stores the
configuration, migrations, and SQL--not those large local files. On another
computer, clone or pull the repository, repeat the Docker/model/migration
commands above, ingest the licensed textbook, and call `embed_chunks()` again.
