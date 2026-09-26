-- Generated from Alembic migrations. Do not edit manually.

BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 0001_create_schemas

CREATE EXTENSION IF NOT EXISTS vector;

CREATE SCHEMA IF NOT EXISTS textbook;

CREATE SCHEMA IF NOT EXISTS sandbox;

INSERT INTO alembic_version (version_num) VALUES ('0001_create_schemas') RETURNING alembic_version.version_num;

COMMIT;

BEGIN;

-- Running upgrade 0001_create_schemas -> 0002_ingestion_tables

CREATE TABLE textbook.books (
    id UUID NOT NULL,
    slug VARCHAR(120) NOT NULL,
    title TEXT NOT NULL,
    authors JSONB NOT NULL,
    canonical_url TEXT NOT NULL,
    license_identifier VARCHAR(80) NOT NULL,
    license_url TEXT NOT NULL,
    attribution TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_books_slug UNIQUE (slug)
);

CREATE TABLE textbook.editions (
    id UUID NOT NULL,
    book_id UUID NOT NULL,
    source_type VARCHAR(40) NOT NULL,
    source_url TEXT NOT NULL,
    source_revision VARCHAR(80) NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_editions_book_revision UNIQUE (book_id, source_revision),
    FOREIGN KEY(book_id) REFERENCES textbook.books (id) ON DELETE CASCADE
);

CREATE TABLE textbook.source_documents (
    id UUID NOT NULL,
    edition_id UUID NOT NULL,
    source_path TEXT NOT NULL,
    source_url TEXT NOT NULL,
    canonical_url TEXT NOT NULL,
    title TEXT NOT NULL,
    ordinal INTEGER NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_source_documents_edition_path UNIQUE (edition_id, source_path),
    FOREIGN KEY(edition_id) REFERENCES textbook.editions (id) ON DELETE CASCADE
);

CREATE TABLE textbook.sections (
    id UUID NOT NULL,
    document_id UUID NOT NULL,
    parent_id UUID,
    level SMALLINT NOT NULL,
    ordinal INTEGER NOT NULL,
    title TEXT NOT NULL,
    heading_path JSONB NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_sections_document_ordinal UNIQUE (document_id, ordinal),
    FOREIGN KEY(document_id) REFERENCES textbook.source_documents (id) ON DELETE CASCADE,
    FOREIGN KEY(parent_id) REFERENCES textbook.sections (id) ON DELETE CASCADE
);

CREATE TABLE textbook.content_blocks (
    id UUID NOT NULL,
    section_id UUID NOT NULL,
    ordinal INTEGER NOT NULL,
    block_type VARCHAR(40) NOT NULL,
    text TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_content_blocks_section_ordinal UNIQUE (section_id, ordinal),
    FOREIGN KEY(section_id) REFERENCES textbook.sections (id) ON DELETE CASCADE
);

CREATE TABLE textbook.chunks (
    id UUID NOT NULL,
    section_id UUID NOT NULL,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    word_count INTEGER NOT NULL,
    content_types TEXT[] NOT NULL,
    heading_path JSONB NOT NULL,
    source_url TEXT NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    text_search TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', text)) STORED NOT NULL,
    embedding VECTOR,
    embedding_model TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_chunks_section_index UNIQUE (section_id, chunk_index),
    FOREIGN KEY(section_id) REFERENCES textbook.sections (id) ON DELETE CASCADE
);

CREATE INDEX ix_chunks_text_search ON textbook.chunks USING gin (text_search);

CREATE TABLE textbook.ingestion_runs (
    id UUID NOT NULL,
    book_id UUID,
    status VARCHAR(20) NOT NULL,
    source_url TEXT NOT NULL,
    source_revision VARCHAR(80) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    finished_at TIMESTAMP WITH TIME ZONE,
    documents_created INTEGER DEFAULT '0' NOT NULL,
    sections_created INTEGER DEFAULT '0' NOT NULL,
    blocks_created INTEGER DEFAULT '0' NOT NULL,
    chunks_created INTEGER DEFAULT '0' NOT NULL,
    error TEXT,
    PRIMARY KEY (id),
    FOREIGN KEY(book_id) REFERENCES textbook.books (id) ON DELETE SET NULL
);

UPDATE alembic_version SET version_num='0002_ingestion_tables' WHERE alembic_version.version_num = '0001_create_schemas';

COMMIT;

BEGIN;

-- Running upgrade 0002_ingestion_tables -> 0003_embedding_search

CREATE EXTENSION IF NOT EXISTS http;

ALTER TABLE textbook.chunks
        ALTER COLUMN embedding TYPE vector(1024)
        USING embedding::vector(1024);

ALTER TABLE textbook.chunks ADD CONSTRAINT ck_chunks_embedding_model CHECK (
        (embedding IS NULL AND embedding_model IS NULL)
        OR
        (
            embedding IS NOT NULL
            AND embedding_model = 'ollama/qwen3-embedding:0.6b'
        )
        );

CREATE INDEX ix_chunks_embedding_hnsw_cosine
        ON textbook.chunks
        USING hnsw (embedding vector_cosine_ops)
        WHERE embedding IS NOT NULL;

COMMENT ON COLUMN textbook.chunks.embedding IS
        'L2-normalized 1024-dimensional embedding from Ollama qwen3-embedding:0.6b';

COMMENT ON COLUMN textbook.chunks.embedding_model IS
        'Exact embedding runtime and model; NULL until the chunk is embedded';

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
            v_embedding vector(1024);
        BEGIN
            IF p_input_kind = 'query' THEN
                v_input :=
                    'Instruct: Given a web search query, retrieve relevant passages that answer the query'
                    || E'\nQuery: '
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
                    'dimensions', 1024,
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
                ((v_response -> 'embeddings' -> 0)::text)::vector(1024);

            IF vector_dims(v_embedding) <> 1024 THEN
                RAISE EXCEPTION
                    'Expected a 1024-dimensional embedding, received %',
                    vector_dims(v_embedding);
            END IF;

            RETURN v_embedding;
        END
        $function$;

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
                    embedding_model = 'ollama/qwen3-embedding:0.6b'
                WHERE id = v_chunk.id;

                v_completed := v_completed + 1;

                IF v_completed % 10 = 0 OR v_completed = v_total THEN
                    RAISE NOTICE 'Embedded % of % chunks', v_completed, v_total;
                END IF;
            END LOOP;

            ANALYZE textbook.chunks;
        END
        $procedure$;

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
                    AND c.embedding_model = 'ollama/qwen3-embedding:0.6b'
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
        $function$;

COMMENT ON FUNCTION textbook.ollama_embed(text, text, text) IS
        'Request one normalized 1024-dimensional Qwen embedding from the private Ollama service';

COMMENT ON PROCEDURE textbook.embed_chunks(boolean) IS
        'Generate SQL-driven embeddings for missing chunks, or all chunks when p_force is true';

COMMENT ON FUNCTION textbook.search_chunks_hybrid(
            text,
            integer,
            integer,
            real,
            real
        ) IS
        'Embed a question and combine PostgreSQL full-text and cosine-vector ranks with RRF';

UPDATE alembic_version SET version_num='0003_embedding_search' WHERE alembic_version.version_num = '0002_ingestion_tables';

COMMIT;
