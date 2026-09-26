# Database files

- [alembic.ini](alembic.ini) — Alembic configuration.
- [migrations/](migrations/) — versioned database changes; the source of truth.
- [postgres/Dockerfile](postgres/Dockerfile) — PostgreSQL image setup.
- [postgres/init/001-enable-vector.sql](postgres/init/001-enable-vector.sql) — first-boot setup.
- [sql/schema.sql](sql/schema.sql) — generated database-creation reference.
- [sql/embed_and_search.sql](sql/embed_and_search.sql) — embedding and search commands for DBeaver.
