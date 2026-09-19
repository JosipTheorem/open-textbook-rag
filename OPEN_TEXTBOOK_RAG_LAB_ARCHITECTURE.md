# Open Textbook RAG Lab

## 1. Project Overview

**Open Textbook RAG Lab** is a local-first study and experimentation platform for turning openly licensed or user-authorized online textbooks into grounded AI learning companions.

Recommended GitHub repository name:

```text
open-textbook-rag-lab
```

The first supported textbook will be **The Nature of Code** by Daniel Shiffman. The second will be **Dive into Deep Learning**, which will verify that the architecture is reusable rather than tailored to one book.

The project should demonstrate practical knowledge of:

- Python, FastAPI, Pydantic, SQLAlchemy and Alembic
- PostgreSQL, pgvector and full-text search
- structured HTML and Markdown ingestion
- hierarchy-aware parsing and chunking
- embeddings, hybrid retrieval and reranking
- local LLM inference and optional cloud APIs
- Docker, testing, CI/CD and experiment tracking
- frontend integration and learning-oriented UX

The project is intended to be both:

1. a genuinely useful study tool, and
2. a strong portfolio project demonstrating production-oriented AI engineering.

---

## 2. Product Idea

The system imports an authorized textbook while preserving its educational structure:

```text
book
  chapter
    section
      subsection
        paragraph / equation / code / figure caption / exercise
```

It creates a searchable knowledge base supporting:

- grounded questions and answers,
- section and chapter explanations,
- Socratic tutoring,
- quizzes and flashcards,
- prerequisite discovery,
- code explanation,
- concept comparison,
- study planning,
- source-linked citations,
- progress and weak-topic tracking.

The platform must clearly distinguish between:

```text
SUPPORTED BY THE TEXTBOOK
and
ADDITIONAL MODEL KNOWLEDGE
```

In strict textbook mode, unsupported answers must be refused or explicitly marked as unsupported by the indexed material.

---

## 3. Initial Textbooks

### 3.1 The Nature of Code

Primary source:

```text
https://natureofcode.com/
```

Why it is a strong first corpus:

- fun and visually interesting subject matter,
- clear chapter and section hierarchy,
- mathematical explanations,
- p5.js code examples,
- diagrams and figure captions,
- exercises and creative projects,
- topics spanning physics, simulation, autonomous agents, evolution and neural networks.

License:

```text
CC BY-NC-SA 4.0
```

The application must preserve attribution, link to the original source, identify the license, and stay within its noncommercial and share-alike requirements when redistributing adapted content.

### 3.2 Dive into Deep Learning

Secondary validation sources:

```text
https://d2l.ai/
https://github.com/d2l-ai/d2l-en
```

Why it is useful as a second corpus:

- structured notebooks and Markdown,
- prose, equations, figures and executable code,
- a different content structure from The Nature of Code,
- a strong test of cross-book ingestion and retrieval.

License summary:

```text
book content: CC BY-SA 4.0
sample/reference code: modified MIT license
```

### 3.3 Future Sources

Future books may be added only when at least one condition is true:

- the material has an explicit compatible open license,
- the user owns or is authorized to process the material,
- the content is supplied directly by the user for private local use.

The platform must not assume that content which is free to read is also free to copy, redistribute, embed or process with generative AI.

---

## 4. Main Design Principles

### 4.1 Separate the Core Layers

```text
INGESTION
from
RETRIEVAL
from
TUTOR BEHAVIOR
from
MODEL GENERATION
```

The core retrieval pipeline must work without an agent. This permits fair comparison of models using identical retrieved evidence.

### 4.2 Preserve Structure Before Chunking

Textbooks must not be flattened into one long string. Chapter, section, code, equation, figure and exercise relationships must survive ingestion.

### 4.3 Citations Are a Product Requirement

Answers should cite the exact book, chapter, section and original URL or local location. Citations must be inspectable by the user.

### 4.4 Content Is External to Application Code

The Git repository should contain ingestion and application code, not copied textbook corpora, generated embeddings or reconstructed books. Content should be fetched or imported locally according to its license and source manifest.

### 4.5 Build Vertically

First prove:

```text
one chapter
  -> structured ingestion
  -> chunking
  -> embeddings
  -> retrieval
  -> cited answer
```

Only then add the full book, more formats and advanced tutor behavior.

---

## 5. High-Level Architecture

```text
                         OPEN TEXTBOOK RAG LAB

┌──────────────────────────────────────────────────────────────┐
│                       Study Interface                        │
│          chat / sources / quizzes / notes / progress        │
└──────────────────────────────┬───────────────────────────────┘
                               │ HTTP / streaming
                               ▼
                    ┌──────────────────────┐
                    │       FastAPI        │
                    │ /chat  /search       │
                    │ /books /ingestion    │
                    │ /quizzes /benchmarks │
                    └──────────┬───────────┘
                               │
             ┌─────────────────┼──────────────────┐
             │                 │                  │
             ▼                 ▼                  ▼
       RAG Service       Tutor Service       Job Queue
             │                 │                  │
             │                 │                  ▼
             │                 │          Ingestion Worker
             │                 │                  │
             │                 │       ┌──────────┴─────────┐
             │                 │       ▼                    ▼
             │                 │   Source Loader      File Loader
             │                 │  HTML / Git repo    PDF / EPUB
             │                 │       │
             │                 │       ▼
             │                 │   Raw Object Store
             │                 │       │
             │                 │       ▼
             │                 │ Structure Extraction
             │                 │       │
             │                 │       ▼
             │                 │ Hierarchy-aware Chunking
             │                 │       │
             │                 │       ▼
             │                 │ Local Embeddings
             │                 │       │
             └─────────────────┴───────┘
                               ▼
                     PostgreSQL + pgvector
                     ─────────────────────
                     books and editions
                     chapters and sections
                     content blocks and chunks
                     embeddings and full-text index
                     notes and quiz attempts
                     ingestion and benchmark runs

                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
                Local LLMs           Cloud LLM APIs
                  Ollama             optional providers
```

---

## 6. Hardware and Technology

Primary machine:

- Intel Core i5-14400F
- NVIDIA RTX 5070 with 12 GB VRAM
- 32 GB RAM

Initial stack:

- Python 3.12+
- FastAPI, Pydantic, SQLAlchemy and Alembic
- PostgreSQL with pgvector
- MinIO for authorized raw snapshots
- Ollama for local generation and embeddings
- pytest, ruff and mypy
- Docker Compose for infrastructure

Start with an approximately 8B local instruction model. Test an approximately 14B quantized model later. Ollama should initially run directly on the host to avoid unnecessary GPU-container complexity.

Do not introduce a second vector database. Use synchronous CLI ingestion for the first milestone; add Redis and Celery only after the vertical slice works.

---

## 7. Source Manifests and Licensing

Every imported book must have a source manifest.

Example:

```yaml
id: nature-of-code
title: The Nature of Code
authors:
  - Daniel Shiffman
source_type: git
source_url: https://github.com/nature-of-code/noc-book-2
canonical_url: https://natureofcode.com/
license: CC-BY-NC-SA-4.0
attribution: Daniel Shiffman, published by No Starch Press
commercial_use_allowed: false
content_version: git-commit-sha
```

The ingestion system must record:

- canonical source URL,
- authors and publisher where applicable,
- license identifier,
- required attribution,
- content version or Git commit,
- ingestion timestamp and content hash,
- whether redistribution and commercial use are allowed.

Unknown or incompatible licensing should stop public redistribution. It must not be silently treated as permission.

---

## 8. Source and File Loaders

Create a common loader abstraction:

```python
class BookLoader:
    def inspect(self, source):
        ...

    def fetch(self, source):
        ...

    def extract_structure(self, raw_content):
        ...
```

Planned implementations:

```text
GitMarkdownBookLoader
HTMLBookLoader
PDFBookLoader          later
EPUBBookLoader         later
```

Use the most structured official source available. For The Nature of Code, prefer its official source repository over scraping rendered pages when practical.

---

## 9. Content Model

Content should move through explicit stages:

```text
SOURCE
  ↓
RAW SNAPSHOT
  ↓
BOOK + EDITION
  ↓
CHAPTER / SECTION TREE
  ↓
TYPED CONTENT BLOCKS
  ↓
RETRIEVAL CHUNKS
  ↓
EMBEDDINGS + FULL-TEXT INDEX
```

Supported content block types should eventually include:

```text
heading
paragraph
definition
equation
code
figure
figure_caption
example
exercise
quotation
callout
```

The first milestone only needs headings, paragraphs and code blocks, but the schema should permit additional types.

---

## 10. Initial Database Schema

### books

```text
id UUID PK
slug VARCHAR UNIQUE
title TEXT
authors JSONB
canonical_url TEXT
license_identifier VARCHAR
attribution TEXT
created_at TIMESTAMP
updated_at TIMESTAMP
```

### editions

```text
id UUID PK
book_id UUID FK -> books.id
version VARCHAR
source_type VARCHAR
source_url TEXT
source_revision VARCHAR nullable
content_hash VARCHAR
raw_object_key TEXT
ingested_at TIMESTAMP
```

### sections

```text
id UUID PK
edition_id UUID FK -> editions.id
parent_id UUID nullable FK -> sections.id
section_type VARCHAR
ordinal INTEGER
number VARCHAR nullable
title TEXT
canonical_url TEXT nullable
path TEXT
depth INTEGER
created_at TIMESTAMP
```

### content_blocks

```text
id UUID PK
section_id UUID FK -> sections.id
ordinal INTEGER
block_type VARCHAR
text TEXT
language VARCHAR nullable
metadata JSONB
created_at TIMESTAMP
```

### chunks

```text
id UUID PK
section_id UUID FK -> sections.id
start_block_id UUID nullable
end_block_id UUID nullable
chunk_index INTEGER
text TEXT
token_count INTEGER
embedding VECTOR(...)
text_search TSVECTOR
metadata JSONB
created_at TIMESTAMP
```

### ingestion_jobs

```text
id UUID PK
book_id UUID nullable
status VARCHAR
started_at TIMESTAMP
finished_at TIMESTAMP nullable
sections_created INTEGER
chunks_created INTEGER
error TEXT nullable
```

Later tables:

```text
notes
bookmarks
quiz_sets
quiz_questions
quiz_attempts
study_sessions
benchmark_questions
benchmark_runs
benchmark_results
```

---

## 11. Structure-Aware Chunking

Each chunk should retain:

- book and edition,
- chapter and section ancestry,
- canonical URL or source location,
- contained content types,
- heading path,
- code language where applicable.

Initial configuration:

```yaml
chunking:
  target_tokens: 500
  overlap_tokens: 75
  never_cross_section_boundary: true
  preserve_code_blocks: true
  prepend_heading_path: true
```

Do not split a code block or equation merely to hit an exact token count. Later experiments can compare fixed-size, structure-aware and parent-child retrieval.

---

## 12. Retrieval Architecture

Implement:

```text
DenseRetriever
LexicalRetriever
HybridRetriever
HierarchyExpander
Reranker          later
```

Initial hybrid flow:

```text
query
 ├──────────────┐
 ▼              ▼
dense        lexical
top 20        top 20
 └──────┬───────┘
        ▼
       RRF
        ▼
hierarchy expansion
        ▼
final top K with section context
```

Hierarchy expansion may attach a section heading, nearby definition, adjacent explanation, or referenced code and figure captions.

Support filtering by book, edition, chapter, content type and code language.

---

## 13. Core RAG Service

Create deterministic functions independent of tutor behavior:

```python
retrieve(query, options)
expand_context(chunks, options)
build_context(chunks)
generate_answer(query, context, model)
```

Return structured results:

```json
{
  "answer": "...",
  "support_status": "supported",
  "citations": [],
  "retrieved_chunks": [],
  "book": "nature-of-code",
  "model": "...",
  "retrieval_strategy": "hybrid",
  "latency_ms": 0
}
```

Supported statuses:

```text
supported
partially_supported
unsupported
```

The model must not invent citations or imply that outside knowledge came from the book.

---

## 14. Tutor Modes

Tutor behavior is an application layer over retrieval.

### Explain

Explain a concept using retrieved passages, adapting depth to the learner while preserving citations.

### Socratic

Guide the learner with questions and hints instead of immediately revealing the complete solution.

### Quiz

Generate questions from selected sections and evaluate answers against retrieved evidence.

### Compare

Compare concepts within one book or across books while citing each source independently.

### Code Walkthrough

Explain a retrieved code example and connect its parts to the relevant textbook discussion.

Generated quizzes and explanations are application outputs, not original textbook content, and must be labeled accordingly.

---

## 15. Provider Abstractions

### Embeddings

```python
class EmbeddingProvider:
    def embed_documents(self, texts):
        ...

    def embed_query(self, text):
        ...
```

Initial implementation: `OllamaEmbeddingProvider`.

### Generation

```python
class LLMProvider:
    def generate(self, messages, **options):
        ...
```

Initial implementation: `OllamaProvider`. Add one frontier provider later. Provider-specific calls must not be scattered throughout the application.

---

## 16. Configuration

Use YAML configuration plus environment variables:

```text
config/
  base.yaml
  local.yaml.example
  benchmark.yaml
```

Example:

```yaml
retrieval:
  strategy: hybrid
  dense_top_k: 20
  lexical_top_k: 20
  final_top_k: 5
  fusion: rrf
  hierarchy_expansion: true

chunking:
  target_tokens: 500
  overlap_tokens: 75
  never_cross_section_boundary: true
  preserve_code_blocks: true

embedding:
  provider: ollama
  model: embedding-model-name

llm:
  provider: ollama
  model: local-model-name
  temperature: 0.0

answering:
  strict_grounding: true
  include_citations: true
```

Secrets belong in `.env`, which must never be committed. Provide `.env.example`.

---

## 17. Docker and Runtime

Initial Docker Compose services:

```text
postgres + pgvector
minio
```

Later services:

```text
api
worker
redis
mlflow
frontend
```

Ollama should initially run on the host.

---

## 18. Evaluation and Benchmarking

Measure retrieval separately from generation.

### Retrieval Metrics

- Recall@K for known supporting sections
- Mean Reciprocal Rank
- section-path accuracy
- citation accuracy
- code-block retrieval accuracy

### Answer Metrics

- correctness
- faithfulness to retrieved evidence
- unsupported-claim rate
- insufficient-context behavior
- citation completeness
- latency and tokens per second

### Tutor Metrics

- quiz alignment with source material
- hint leakage in Socratic mode
- difficulty calibration
- learner-rated usefulness later

Use textbook review questions and manually curated questions where licensing permits. Do not rely entirely on LLM-as-a-judge.

Model comparison must use:

```text
same question
+ same retrieved evidence
+ different model
```

---

## 19. Testing

Use pytest.

### Unit Tests

- source manifest validation
- heading hierarchy extraction
- Markdown/HTML normalization
- code-block preservation
- structure-aware chunking
- RRF
- citation construction
- configuration loading

### Integration Tests

- PostgreSQL write/read
- pgvector retrieval
- full-text search
- MinIO object storage
- ingestion from saved fixtures
- CLI question-answer flow
- FastAPI endpoints later

CI must never depend on live textbook websites. Store small, license-compatible fixtures with attribution or synthetic fixtures.

---

## 20. Repository Structure

```text
open-textbook-rag-lab/

├── apps/
│   ├── api/
│   ├── worker/
│   └── frontend/
├── src/
│   └── textbook_rag/
│       ├── config/
│       ├── db/
│       ├── ingestion/
│       │   ├── loaders/
│       │   ├── manifests/
│       │   ├── extractors/
│       │   ├── normalizers/
│       │   ├── chunking/
│       │   └── pipeline.py
│       ├── storage/
│       ├── embeddings/
│       ├── retrieval/
│       ├── rag/
│       ├── llm/
│       ├── tutoring/
│       ├── evaluation/
│       └── services/
├── book_sources/
│   ├── nature-of-code.yaml
│   └── dive-into-deep-learning.yaml
├── migrations/
├── tests/
│   ├── fixtures/
│   ├── unit/
│   └── integration/
├── config/
├── scripts/
│   ├── ingest_book.py
│   └── ask_book.py
├── .github/workflows/
├── compose.yaml
├── Dockerfile
├── pyproject.toml
├── .env.example
├── .gitignore
├── LICENSE
├── THIRD_PARTY_CONTENT.md
└── README.md
```

Downloaded books, raw snapshots, embeddings, database volumes and generated study artifacts must be ignored by Git.

---

## 21. Implementation Phases

### Phase 0 — Repository Bootstrap

Create:

- Python package and `pyproject.toml`
- configuration and logging
- tests
- `.env.example` and `.gitignore`
- README skeleton
- `THIRD_PARTY_CONTENT.md`
- source manifest schema

Add ruff, mypy and pytest.

### Phase 1 — Local Infrastructure

Set up PostgreSQL with pgvector, MinIO, SQLAlchemy, Alembic, initial models and health checks. Do not add Redis or Celery yet.

### Phase 2 — Nature of Code Vertical Slice

Ingest only:

```text
Introduction
Chapter 0 — Randomness
Chapter 1 — Vectors
Chapter 2 — Forces
```

Requirements:

- use the authorized official source,
- record source revision and license metadata,
- store a raw snapshot locally,
- preserve chapter and section hierarchy,
- normalize headings, paragraphs and code blocks,
- create structure-aware chunks,
- retain original URLs and attribution.

Implement ingestion first as a synchronous CLI.

### Phase 3 — Embeddings and Retrieval

- connect to Ollama,
- generate local embeddings,
- store them in pgvector,
- implement dense and full-text search,
- implement RRF hybrid retrieval,
- print sections, scores and source URLs from a CLI.

### Phase 4 — Grounded Study Answers

- implement `LLMProvider` and `OllamaProvider`,
- implement the deterministic RAG service,
- add strict grounding and insufficient-context behavior,
- produce section-linked citations,
- expose `ask_book.py` CLI.

This is the first major milestone.

### Phase 5 — Retrieval Evaluation

Create a small manually verified question set, measure Recall@K and citation accuracy, compare retrieval strategies, and repair retrieval before adding complex tutor behavior.

### Phase 6 — Tutor Modes

Add Explain, Socratic, Quiz and Code Walkthrough modes over the same retrieval service.

### Phase 7 — FastAPI

```text
GET  /health
GET  /api/books
GET  /api/books/{book_id}/sections
POST /api/search
POST /api/chat
POST /api/quizzes
```

### Phase 8 — Second Book Validation

Add Dive into Deep Learning using its structured source. Both books must use the same normalized model and retrieval API.

### Phase 9 — Async Ingestion

Add Redis, Celery and ingestion-job endpoints only after synchronous ingestion is reliable.

### Phase 10 — Browser Study Interface

Support book/chapter selection, grounded chat, citation inspection, quizzes, notes and study history.

### Phase 11 — Additional Formats

Add PDF and EPUB loaders with layout and structure validation. Do not treat raw PDF extraction as reliable without visual and structural tests.

### Phase 12 — Model Benchmarking

Compare local models against one frontier provider using identical evidence. Log runs and metrics with MLflow.

### Phase 13 — Portfolio Polish

Add GitHub Actions, architecture diagrams, screenshots, example queries, evaluation plots, setup instructions, and complete licensing documentation.

---

## 22. First Milestone Definition

Milestone 1 is complete when:

```text
1. PostgreSQL + pgvector starts locally.
2. MinIO starts locally.
3. A valid Nature of Code source manifest is loaded.
4. Introduction and Chapters 0–2 are imported.
5. Raw authorized source data is stored locally.
6. Chapter and section hierarchy is preserved.
7. Paragraphs and code blocks are chunked without structural damage.
8. Ollama generates embeddings.
9. Embeddings are stored in pgvector.
10. A CLI accepts a question.
11. Hybrid retrieval returns relevant sections.
12. A local model answers using only retrieved material.
13. The terminal prints support status and source-linked citations.
14. A small evaluation set verifies retrieval and citation behavior.
```

Nothing else is required for the first milestone.

---

## 23. Initial Codex Task

Start by implementing **Phase 0 and Phase 1 only**.

Required initial output:

```text
project structure
pyproject.toml
configuration loader
source manifest schema
The Nature of Code manifest
.env.example
.gitignore
THIRD_PARTY_CONTENT.md
Docker Compose
PostgreSQL + pgvector
MinIO
SQLAlchemy setup
Alembic setup
initial database models
health-check script/tests
README setup instructions
```

Do not implement the full architecture at once.

---

## 24. Coding Guidelines

- Prefer simple, readable Python with type hints.
- Keep domain logic outside HTTP route handlers.
- Keep provider-specific code behind interfaces.
- Avoid global mutable state.
- Use dependency injection where it improves testing.
- Preserve source hierarchy and provenance.
- Treat licensing metadata as required data.
- Use structured logging and meaningful domain exceptions.
- Write deterministic tests for parsing and retrieval logic.
- Avoid abstractions until two implementations need them.

---

## 25. Security and Content Practices

- Never commit API keys, `.env`, databases or object-store volumes.
- Do not commit downloaded textbooks unless their license and attribution requirements explicitly permit the chosen distribution model.
- Treat imported HTML, Markdown and book files as untrusted input.
- Sanitize rendered HTML.
- Never automatically execute imported textbook code.
- Run future code-execution features inside an isolated sandbox.
- Add timeouts and size limits to remote downloads.
- Respect source terms and robots directives where relevant.
- Preserve canonical source URLs and attribution.
- Keep a content-removal path for imported material.

---

## 26. Non-Goals for the First Version

Do not initially build:

- arbitrary web crawling,
- support for every ebook format,
- automatic execution of generated or imported code,
- multi-agent systems,
- Kubernetes, authentication or cloud deployment,
- mobile applications,
- a marketplace of copyrighted books,
- fine-tuning or model training,
- complex learner analytics,
- a polished frontend before retrieval works.

---

## 27. Portfolio Story

> Open Textbook RAG Lab is a local-first learning platform that transforms openly licensed or user-authorized technical textbooks into grounded AI study companions. It preserves book hierarchy, code, equations, figures and source provenance; performs hybrid SQL/vector retrieval; produces section-linked answers and tutor experiences; supports local consumer-GPU models and optional frontier APIs; and provides a reproducible benchmark environment for evaluating retrieval, faithfulness and learning-oriented behavior across different models and textbooks.

That statement is the architectural north star of the project.
