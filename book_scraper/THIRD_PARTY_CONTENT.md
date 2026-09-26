# Third-party textbook content

The repository contains ingestion code and source manifests, not copied textbook
corpora, generated chunks, or embeddings.

## Dive into Deep Learning

- Authors: Aston Zhang, Zachary C. Lipton, Mu Li, and Alexander J. Smola
- Official website: https://d2l.ai/
- Official source: https://github.com/d2l-ai/d2l-en
- Book license: CC BY-SA 4.0
- License: https://creativecommons.org/licenses/by-sa/4.0/
- Sample/reference code: separate modified MIT license in the source repository

Local source snapshots are downloaded into ignored `book_scraper/data/raw/` directories.
Database records retain the source URL, exact Git revision, license, attribution,
and content hashes. If transformed book content is shared, the attribution and
ShareAlike obligations of CC BY-SA 4.0 must be preserved.

## Embedding model and local software

- Qwen3-Embedding-0.6B model: Apache-2.0
- Official model card: https://huggingface.co/Qwen/Qwen3-Embedding-0.6B
- Ollama model tag: `qwen3-embedding:0.6b`
- Ollama project: MIT, https://github.com/ollama/ollama
- pgsql-http extension: MIT, https://github.com/pramsey/pgsql-http
- pgvector extension: PostgreSQL License, https://github.com/pgvector/pgvector

The repository does not contain the model weights or third-party container
images. Docker and Ollama download them locally from their official registries.
