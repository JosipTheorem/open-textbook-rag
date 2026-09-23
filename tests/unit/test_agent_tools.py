from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from textbook_agent.config import AgentSettings
from textbook_agent.tools import hybrid_search


def test_hybrid_search_returns_json_safe_evidence() -> None:
    row = {
        "section_title": "Machine Learning",
        "chunk_text": "Machine learning uses experience to improve performance.",
        "source_url": "https://example.test/book/chapter.html",
        "semantic_similarity": Decimal("0.81"),
        "lexical_score": Decimal("0.42"),
        "hybrid_score": Decimal("0.03"),
    }
    cursor = MagicMock()
    cursor.fetchall.return_value = [row]
    connection = MagicMock()
    connection.execute.return_value = cursor
    context = MagicMock()
    context.__enter__.return_value = connection

    settings = AgentSettings(database_url="postgresql://example")
    with patch("textbook_agent.tools.connect", return_value=context) as connect_mock:
        results = hybrid_search("machine learning", 3, settings=settings)

    assert results[0]["section_title"] == "Machine Learning"
    assert results[0]["semantic_similarity"] == 0.81
    assert connect_mock.call_args.kwargs["connect_timeout"] == 5
    assert connect_mock.call_count == 1
    connection.execute.assert_called_once()


def test_hybrid_search_converts_missing_scores_to_zero() -> None:
    row = {
        "section_title": "Introduction",
        "chunk_text": "Evidence",
        "source_url": "https://example.test/book",
        "semantic_similarity": None,
        "lexical_score": None,
        "hybrid_score": None,
    }
    cursor = MagicMock()
    cursor.fetchall.return_value = [row]
    connection = MagicMock()
    connection.execute.return_value = cursor
    context = MagicMock()
    context.__enter__.return_value = connection

    with patch("textbook_agent.tools.connect", return_value=context):
        results = hybrid_search(
            "evidence",
            settings=AgentSettings(database_url="postgresql://example"),
        )

    assert results[0]["semantic_similarity"] == 0.0
    assert results[0]["lexical_score"] == 0.0
    assert results[0]["hybrid_score"] == 0.0


@pytest.mark.parametrize("limit", [0, 11])
def test_hybrid_search_rejects_invalid_limits(limit: int) -> None:
    with pytest.raises(ValueError, match="between 1 and 10"):
        hybrid_search("machine learning", limit)


def test_hybrid_search_rejects_empty_query() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        hybrid_search("   ")
