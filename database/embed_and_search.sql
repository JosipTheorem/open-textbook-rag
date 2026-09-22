-- SQL-driven embedding generation and hybrid-search checks.
-- Run each section in DBeaver after following database/README.md.

-- Expected after applying migrations: 0003_embedding_search
SELECT version_num
FROM alembic_version;

-- Confirm that PostgreSQL can reach Ollama and receives 1024 dimensions.
SELECT vector_dims(
    textbook.ollama_embed(
        'A short connection test.',
        'document',
        '0'
    )
) AS test_embedding_dimensions;

-- Generate embeddings for chunks that do not have one yet. This is safe to
-- rerun because it skips chunks that already have embeddings.
CALL textbook.embed_chunks();

-- Expect missing_embeddings = 0, both dimensions = 1024, and one model.
SELECT
    COUNT(*) AS total_chunks,
    COUNT(embedding) AS embedded_chunks,
    COUNT(*) - COUNT(embedding) AS missing_embeddings,
    MIN(vector_dims(embedding)) AS minimum_dimension,
    MAX(vector_dims(embedding)) AS maximum_dimension,
    array_agg(DISTINCT embedding_model)
        FILTER (WHERE embedding_model IS NOT NULL) AS embedding_models
FROM textbook.chunks;

-- The only search entry point: query embedding + text search + vector search
-- + reciprocal-rank fusion happen inside this function.
SELECT
    section_title,
    semantic_similarity,
    lexical_score,
    hybrid_score,
    left(chunk_text, 300) AS preview,
    source_url
FROM textbook.search_chunks_hybrid(
    'What is machine learning?',
    5
);

-- Only use this after deliberately changing the embedding implementation or
-- when you explicitly want to regenerate every stored vector:
-- CALL textbook.embed_chunks(true);
