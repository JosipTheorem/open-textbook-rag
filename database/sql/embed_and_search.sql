-- Run after the database migrations and textbook import.
-- Embeds only chunks that do not have an embedding yet.
CALL textbook.embed_chunks();

-- Change the question and result count to search your books.
SELECT *
FROM textbook.search_chunks_hybrid('What is machine learning?', 5);
