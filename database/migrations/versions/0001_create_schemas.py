"""Create permanent and experimental database schemas."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0001_create_schemas"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Enable pgvector and create the project schemas."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE SCHEMA IF NOT EXISTS textbook")
    op.execute("CREATE SCHEMA IF NOT EXISTS sandbox")


def downgrade() -> None:
    """Remove empty schemas and the vector extension."""
    op.execute("DROP SCHEMA IF EXISTS sandbox RESTRICT")
    op.execute("DROP SCHEMA IF EXISTS textbook RESTRICT")
    op.execute("DROP EXTENSION IF EXISTS vector")
