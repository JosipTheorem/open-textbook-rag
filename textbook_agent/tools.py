"""Tools exposed to the textbook agent."""

from __future__ import annotations

import json
from typing import Annotated, Any

from langchain.tools import tool
from psycopg import OperationalError, connect
from psycopg.rows import dict_row
from pydantic import Field
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from textbook_agent.config import AgentSettings


@retry(
    retry=retry_if_exception_type(OperationalError),
    stop=stop_after_attempt(3),
    wait=wait_fixed(0.5),
    reraise=True,
)
def _open_connection(settings: AgentSettings) -> Any:
    """Open PostgreSQL with a bounded retry for transient local socket failures."""
    return connect(
        settings.psycopg_dsn,
        row_factory=dict_row,
        connect_timeout=5,
    )


def hybrid_search(
    query: str,
    limit: int = 5,
    *,
    settings: AgentSettings | None = None,
) -> list[dict[str, Any]]:
    """Run the database-owned hybrid search and return JSON-safe evidence rows."""
    if not query.strip():
        raise ValueError("Search query must not be empty.")
    if not 1 <= limit <= 10:
        raise ValueError("Search limit must be between 1 and 10.")

    active_settings = settings or AgentSettings()
    with _open_connection(active_settings) as connection:
        rows = connection.execute(
            """
            SELECT
                section_title,
                chunk_text,
                source_url,
                semantic_similarity,
                lexical_score,
                hybrid_score
            FROM textbook.search_chunks_hybrid(%s, %s)
            """,
            (query.strip(), limit),
        ).fetchall()

    return [
        {
            "section_title": row["section_title"],
            "chunk_text": row["chunk_text"],
            "source_url": row["source_url"],
            "semantic_similarity": float(row["semantic_similarity"] or 0.0),
            "lexical_score": float(row["lexical_score"] or 0.0),
            "hybrid_score": float(row["hybrid_score"] or 0.0),
        }
        for row in rows
    ]


@tool
def search_textbook(
    query: Annotated[
        str,
        Field(description="English-only textbook search query; translate Croatian questions first."),
    ],
    limit: Annotated[
        int,
        Field(ge=1, le=10, description="Number of evidence chunks to return."),
    ] = 5,
) -> str:
    """Search the textbook with PostgreSQL full-text and vector retrieval.

    Use this tool before answering any factual question about textbook content.
    The result is JSON containing evidence text, section titles, relevance scores,
    and source URLs that must be cited in the final answer.
    """
    return json.dumps(hybrid_search(query, limit), ensure_ascii=False)
