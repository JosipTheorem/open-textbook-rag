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
