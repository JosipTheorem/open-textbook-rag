"""Generate Qwen embeddings through Ollama and add hybrid search."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0003_embedding_search"
down_revision: str | None = "0002_ingestion_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


EMBEDDING_MODEL = "ollama/qwen3-embedding:0.6b"
EMBEDDING_DIMENSION = 1024


def upgrade() -> None:
    """Add SQL-driven embedding generation and one hybrid search function."""
    op.execute("CREATE EXTENSION IF NOT EXISTS http")

    op.execute(
        f"""
        ALTER TABLE textbook.chunks
        ALTER COLUMN embedding TYPE vector({EMBEDDING_DIMENSION})
        USING embedding::vector({EMBEDDING_DIMENSION})
        """
    )

    op.create_check_constraint(
        "ck_chunks_embedding_model",
        "chunks",
        f"""
        (embedding IS NULL AND embedding_model IS NULL)
        OR
        (
            embedding IS NOT NULL
            AND embedding_model = '{EMBEDDING_MODEL}'
        )
        """,
        schema="textbook",
    )

    op.execute(
        """
        CREATE INDEX ix_chunks_embedding_hnsw_cosine
        ON textbook.chunks
        USING hnsw (embedding vector_cosine_ops)
        WHERE embedding IS NOT NULL
        """
    )

    op.execute(
        f"""
        COMMENT ON COLUMN textbook.chunks.embedding IS
        'L2-normalized {EMBEDDING_DIMENSION}-dimensional embedding from Ollama qwen3-embedding:0.6b'
        """
    )
    op.execute(
        """
        COMMENT ON COLUMN textbook.chunks.embedding_model IS
        'Exact embedding runtime and model; NULL until the chunk is embedded'
        """
    )

    op.execute(
        f"""
        CREATE FUNCTION textbook.ollama_embed(
            p_input text,
            p_input_kind text DEFAULT 'document',
            p_keep_alive text DEFAULT '5m'
        )
        RETURNS vector
        LANGUAGE plpgsql
        VOLATILE
        PARALLEL UNSAFE
        STRICT
        AS $function$
        DECLARE
            v_input text;
            v_status integer;
            v_response_text text;
            v_response jsonb;
            v_embedding vector({EMBEDDING_DIMENSION});
        BEGIN
            IF p_input_kind = 'query' THEN
                v_input :=
                    'Instruct: Given a web search query, retrieve relevant passages that answer the query'
                    || E'\\nQuery: '
                    || p_input;
            ELSIF p_input_kind = 'document' THEN
                v_input := p_input;
            ELSE
                RAISE EXCEPTION
                    'p_input_kind must be query or document, received: %',
                    p_input_kind;
            END IF;

            PERFORM public.http_set_curlopt(
                'CURLOPT_CONNECTTIMEOUT_MS',
                '5000'
            );
            PERFORM public.http_set_curlopt('CURLOPT_TIMEOUT_MS', '120000');

            SELECT response.status, response.content
            INTO v_status, v_response_text
            FROM public.http_post(
                'http://ollama-embeddings:11434/api/embed',
                jsonb_build_object(
                    'model', 'qwen3-embedding:0.6b',
                    'input', v_input,
                    'dimensions', {EMBEDDING_DIMENSION},
                    'truncate', false,
                    'keep_alive', p_keep_alive
                )::text,
                'application/json'
            ) AS response;

            IF v_status <> 200 THEN
                RAISE EXCEPTION
                    'Ollama embedding request failed with HTTP %: %',
                    v_status,
                    left(v_response_text, 500);
            END IF;

            v_response := v_response_text::jsonb;

            IF
                jsonb_typeof(v_response -> 'embeddings') IS DISTINCT FROM 'array'
                OR jsonb_array_length(v_response -> 'embeddings') <> 1
            THEN
                RAISE EXCEPTION 'Ollama returned an unexpected embedding response';
            END IF;

            v_embedding :=
                ((v_response -> 'embeddings' -> 0)::text)::vector({EMBEDDING_DIMENSION});

            IF vector_dims(v_embedding) <> {EMBEDDING_DIMENSION} THEN
                RAISE EXCEPTION
                    'Expected a {EMBEDDING_DIMENSION}-dimensional embedding, received %',
                    vector_dims(v_embedding);
            END IF;

            RETURN v_embedding;
        END
        $function$
        """
    )

    op.execute(
        f"""
        CREATE PROCEDURE textbook.embed_chunks(
            p_force boolean DEFAULT false
        )
        LANGUAGE plpgsql
        AS $procedure$
        DECLARE
            v_chunk record;
            v_completed integer := 0;
            v_total integer;
        BEGIN
            SELECT COUNT(*)
            INTO v_total
            FROM textbook.chunks
            WHERE p_force OR embedding IS NULL;

            RAISE NOTICE 'Embedding % textbook chunks', v_total;

            FOR v_chunk IN
                SELECT id, text
                FROM textbook.chunks
                WHERE p_force OR embedding IS NULL
                ORDER BY id
            LOOP
                UPDATE textbook.chunks
                SET
                    embedding = textbook.ollama_embed(
                        v_chunk.text,
                        'document',
                        '5m'
                    ),
                    embedding_model = '{EMBEDDING_MODEL}'
                WHERE id = v_chunk.id;

                v_completed := v_completed + 1;

                IF v_completed % 10 = 0 OR v_completed = v_total THEN
                    RAISE NOTICE 'Embedded % of % chunks', v_completed, v_total;
                END IF;
            END LOOP;

            ANALYZE textbook.chunks;
        END
        $procedure$
        """
    )

    op.execute(
        f"""
        CREATE FUNCTION textbook.search_chunks_hybrid(
            p_query_text text,
            p_match_count integer DEFAULT 10,
            p_rrf_k integer DEFAULT 60,
            p_text_weight real DEFAULT 1.0,
            p_vector_weight real DEFAULT 1.0
        )
        RETURNS TABLE (
            chunk_id uuid,
            book_title text,
            section_title text,
            heading_path jsonb,
            chunk_text text,
            source_url text,
            semantic_similarity double precision,
            lexical_score real,
            hybrid_score double precision
        )
        LANGUAGE sql
        VOLATILE
        PARALLEL UNSAFE
        AS $function$
            WITH settings AS (
                SELECT
                    LEAST(
                        GREATEST(COALESCE(p_match_count, 10), 1),
                        100
                    ) AS result_count,
                    GREATEST(
                        LEAST(
                            GREATEST(COALESCE(p_match_count, 10), 1),
                            100
                        ) * 5,
                        50
                    ) AS candidate_count,
                    GREATEST(COALESCE(p_rrf_k, 60), 1) AS rrf_k,
                    COALESCE(p_text_weight, 1.0)::double precision
                        AS text_weight,
                    COALESCE(p_vector_weight, 1.0)::double precision
                        AS vector_weight
            ),
            query_inputs AS MATERIALIZED (
                SELECT
                    websearch_to_tsquery('english', p_query_text) AS text_query,
                    textbook.ollama_embed(
                        p_query_text,
                        'query',
                        '5m'
                    ) AS query_embedding
            ),
            lexical_scored AS (
                SELECT
                    c.id AS candidate_id,
                    ts_rank_cd(c.text_search, q.text_query)::real
                        AS lexical_score
                FROM textbook.chunks AS c
                CROSS JOIN query_inputs AS q
                WHERE c.text_search @@ q.text_query
                ORDER BY
                    ts_rank_cd(c.text_search, q.text_query) DESC,
                    c.id
                LIMIT (SELECT candidate_count FROM settings)
            ),
            lexical_candidates AS (
                SELECT
                    candidate_id,
                    lexical_score,
                    row_number() OVER (
                        ORDER BY lexical_score DESC, candidate_id
                    ) AS lexical_rank
                FROM lexical_scored
            ),
            vector_nearest AS (
                SELECT
                    c.id AS candidate_id,
                    c.embedding <=> q.query_embedding AS cosine_distance
                FROM textbook.chunks AS c
                CROSS JOIN query_inputs AS q
                WHERE
                    c.embedding IS NOT NULL
                    AND c.embedding_model = '{EMBEDDING_MODEL}'
                ORDER BY
                    c.embedding <=> q.query_embedding,
                    c.id
                LIMIT (SELECT candidate_count FROM settings)
            ),
            vector_candidates AS (
                SELECT
                    candidate_id,
                    1.0 - cosine_distance AS semantic_similarity,
                    row_number() OVER (
                        ORDER BY cosine_distance, candidate_id
                    ) AS vector_rank
                FROM vector_nearest
            ),
            rrf_components AS (
                SELECT
                    lc.candidate_id,
                    settings.text_weight
                        / (settings.rrf_k + lc.lexical_rank) AS score
                FROM lexical_candidates AS lc
                CROSS JOIN settings

                UNION ALL

                SELECT
                    vc.candidate_id,
                    settings.vector_weight
                        / (settings.rrf_k + vc.vector_rank) AS score
                FROM vector_candidates AS vc
                CROSS JOIN settings
            ),
            fused AS (
                SELECT
                    candidate_id,
                    SUM(score) AS hybrid_score
                FROM rrf_components
                GROUP BY candidate_id
            )
            SELECT
                c.id,
                b.title,
                s.title,
                c.heading_path,
                c.text,
                c.source_url,
                vc.semantic_similarity,
                lc.lexical_score,
                f.hybrid_score
            FROM fused AS f
            JOIN textbook.chunks AS c
                ON c.id = f.candidate_id
            JOIN textbook.sections AS s
                ON s.id = c.section_id
            JOIN textbook.source_documents AS d
                ON d.id = s.document_id
            JOIN textbook.editions AS e
                ON e.id = d.edition_id
            JOIN textbook.books AS b
                ON b.id = e.book_id
            LEFT JOIN lexical_candidates AS lc
                ON lc.candidate_id = c.id
            LEFT JOIN vector_candidates AS vc
                ON vc.candidate_id = c.id
            ORDER BY
                f.hybrid_score DESC,
                c.id
            LIMIT (SELECT result_count FROM settings)
        $function$
        """
    )

    op.execute(
        """
        COMMENT ON FUNCTION textbook.ollama_embed(text, text, text) IS
        'Request one normalized 1024-dimensional Qwen embedding from the private Ollama service'
        """
    )
    op.execute(
        """
        COMMENT ON PROCEDURE textbook.embed_chunks(boolean) IS
        'Generate SQL-driven embeddings for missing chunks, or all chunks when p_force is true'
        """
    )
    op.execute(
        """
        COMMENT ON FUNCTION textbook.search_chunks_hybrid(
            text,
            integer,
            integer,
            real,
            real
        ) IS
        'Embed a question and combine PostgreSQL full-text and cosine-vector ranks with RRF'
        """
    )


def downgrade() -> None:
    """Remove SQL embedding support and return to an unbounded vector column."""
    op.execute(
        """
        DROP FUNCTION textbook.search_chunks_hybrid(
            text,
            integer,
            integer,
            real,
            real
        )
        """
    )
    op.execute("DROP PROCEDURE textbook.embed_chunks(boolean)")
    op.execute("DROP FUNCTION textbook.ollama_embed(text, text, text)")
    op.drop_index(
        "ix_chunks_embedding_hnsw_cosine",
        table_name="chunks",
        schema="textbook",
    )
    op.drop_constraint(
        "ck_chunks_embedding_model",
        "chunks",
        schema="textbook",
        type_="check",
    )
    op.execute(
        """
        ALTER TABLE textbook.chunks
        ALTER COLUMN embedding TYPE vector
        USING embedding::vector
        """
    )
    op.execute("DROP EXTENSION IF EXISTS http")
