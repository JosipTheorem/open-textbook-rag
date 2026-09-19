# Open Textbook RAG Lab — Project Board

This file is the version-controlled project board for `open-textbook-rag`.

## How to use this board

1. Move the complete task card between **TO DO**, **DOING**, and **DONE**.
2. Keep no more than two tasks in **DOING** at once.
3. Check acceptance criteria as work is completed.
4. Save the file, stage it with `git add TASK_BOARD.md`, commit, and push.
5. On the other computer, pull before editing the board.

Git records changes to this file, so task status follows the repository between computers. Unlike a standalone HTML board, it does not depend on browser-local storage.

Task priority:

- **P0** — required for the next milestone
- **P1** — important immediately after the milestone
- **P2** — later improvement

---

# TO DO

## Phase 0 — Repository bootstrap

### OTR-003 — Create the Python package structure

**Priority:** P0  
**Description:** Create the initial `src/textbook_rag` package, application folders, scripts folder, and test directories described in the architecture document.

**Acceptance criteria:**

- [ ] `src/textbook_rag/__init__.py` exists.
- [ ] `tests/unit` and `tests/integration` exist.
- [ ] `scripts`, `config`, and `book_sources` exist.
- [ ] Python can import `textbook_rag` from the development environment.

### OTR-004 — Add project metadata and tool configuration

**Priority:** P0  
**Description:** Add `pyproject.toml` containing package metadata and configuration for ruff, mypy and pytest. Keep `requirements.txt` usable for the current workflow.

**Acceptance criteria:**

- [ ] Project requires Python 3.12 or newer.
- [ ] Ruff, mypy and pytest settings are defined.
- [ ] Package discovery uses the `src` layout.
- [ ] `ruff check .`, `mypy src`, and `pytest` can run.

### OTR-005 — Implement typed configuration loading

**Priority:** P0  
**Description:** Load base YAML configuration and environment-variable overrides through Pydantic settings. Validate invalid or missing required values with useful messages.

**Acceptance criteria:**

- [ ] `config/base.yaml` defines database, MinIO, chunking and provider defaults.
- [ ] Secrets come from environment variables, not YAML.
- [ ] Configuration has type hints and validation.
- [ ] Unit tests cover valid configuration and invalid values.

### OTR-006 — Add environment templates and content exclusions

**Priority:** P0  
**Description:** Add `.env.example` and verify `.gitignore` excludes credentials, virtual environments, downloaded books, raw snapshots, embeddings, database volumes and generated artifacts.

**Acceptance criteria:**

- [ ] `.env.example` contains placeholders only.
- [ ] `.env` and `.venv` are ignored.
- [ ] Local content and infrastructure volumes are ignored.
- [ ] `git status` cannot accidentally expose a secret or downloaded textbook.

### OTR-007 — Document third-party content policy

**Priority:** P0  
**Description:** Create `THIRD_PARTY_CONTENT.md` explaining that textbook content remains external, must have an authorized source, and retains its original license and attribution.

**Acceptance criteria:**

- [ ] The Nature of Code attribution is documented.
- [ ] CC BY-NC-SA 4.0 limitations are stated.
- [ ] Dive into Deep Learning licenses are documented.
- [ ] The repository does not claim ownership of imported content.

### OTR-008 — Define and validate book source manifests

**Priority:** P0  
**Description:** Create a typed manifest model describing book identity, canonical URL, source URL, source type, license, attribution and exact content revision.

**Acceptance criteria:**

- [ ] Invalid manifests fail with clear validation messages.
- [ ] Unknown licenses are not silently accepted for redistribution.
- [ ] Content revision and hash fields are supported.
- [ ] Unit tests cover valid and invalid manifests.

### OTR-009 — Add The Nature of Code source manifest

**Priority:** P0  
**Description:** Add `book_sources/nature-of-code.yaml` referencing the official source and required attribution.

**Acceptance criteria:**

- [ ] Canonical website and official source repository are recorded.
- [ ] License is `CC-BY-NC-SA-4.0`.
- [ ] Commercial use is marked false.
- [ ] The manifest passes schema validation.

## Phase 1 — Local infrastructure

### OTR-010 — Create Docker Compose infrastructure

**Priority:** P0  
**Description:** Create `compose.yaml` for PostgreSQL with pgvector and MinIO. Use health checks, named volumes and environment-variable configuration.

**Acceptance criteria:**

- [ ] `docker compose config` succeeds.
- [ ] PostgreSQL becomes healthy.
- [ ] The `vector` extension can be enabled.
- [ ] MinIO becomes healthy and exposes its console locally.
- [ ] Persistent data stays outside Git.

### OTR-011 — Implement database connection management

**Priority:** P0  
**Description:** Add SQLAlchemy engine, session factory and explicit connection lifecycle management using the configured PostgreSQL URL.

**Acceptance criteria:**

- [ ] No connection is opened during module import.
- [ ] Sessions are closed correctly on success and failure.
- [ ] Connection errors are understandable.
- [ ] An integration test verifies a simple query.

### OTR-012 — Configure Alembic migrations

**Priority:** P0  
**Description:** Initialize Alembic against the application metadata and configuration system.

**Acceptance criteria:**

- [ ] Alembic reads the configured database URL.
- [ ] Upgrade and downgrade commands work.
- [ ] Migrations can enable the pgvector extension.
- [ ] Empty schema drift is detectable.

### OTR-013 — Implement the initial database models

**Priority:** P0  
**Description:** Implement models for books, editions, sections, content blocks, chunks and ingestion jobs, including relationships and useful uniqueness constraints.

**Acceptance criteria:**

- [ ] Models match the architecture document.
- [ ] Section parent/child hierarchy is representable.
- [ ] Chunk embeddings use configurable dimensions.
- [ ] Full-text and lookup indexes are defined.
- [ ] An initial migration creates the schema successfully.

### OTR-014 — Implement MinIO object storage adapter

**Priority:** P0  
**Description:** Create a small object-storage interface and MinIO implementation for authorized raw source snapshots.

**Acceptance criteria:**

- [ ] Objects can be uploaded, retrieved and identified by deterministic keys.
- [ ] Content type, hash and source metadata are stored.
- [ ] Missing buckets can be created explicitly.
- [ ] Integration tests verify upload and retrieval.

### OTR-015 — Add infrastructure health checks

**Priority:** P0  
**Description:** Add a script that checks configuration, PostgreSQL, pgvector and MinIO without modifying user data.

**Acceptance criteria:**

- [ ] Each service reports a clear healthy/unhealthy result.
- [ ] Failure exits with a nonzero status.
- [ ] Credentials are never printed.
- [ ] README explains how to run the check.

### OTR-016 — Expand the README setup guide

**Priority:** P0  
**Description:** Document setup for Windows PowerShell, Python 3.12, the virtual environment, dependency installation, Docker services and health verification.

**Acceptance criteria:**

- [ ] Includes activation and no-activation PowerShell commands.
- [ ] Includes Docker startup and shutdown commands.
- [ ] Includes troubleshooting for PowerShell execution policy.
- [ ] New contributors can reproduce Phase 0 and Phase 1.

## Phase 2 — The Nature of Code vertical slice

### OTR-017 — Implement the Git/Markdown book loader

**Priority:** P1  
**Description:** Load an exact revision of an authorized source repository and produce a deterministic raw snapshot without executing source code.

**Acceptance criteria:**

- [ ] Source revision is pinned and recorded.
- [ ] Downloaded content is stored outside Git.
- [ ] Loader rejects unexpected source layouts cleanly.
- [ ] Tests use local fixtures rather than a live network source.

### OTR-018 — Extract textbook hierarchy and typed blocks

**Priority:** P1  
**Description:** Parse headings, paragraphs and fenced code blocks from the Introduction and Chapters 0–2 while preserving ordering and parent sections.

**Acceptance criteria:**

- [ ] Chapter and section paths are stable.
- [ ] Code language is preserved.
- [ ] Canonical section URLs can be produced.
- [ ] Parser fixtures cover headings, prose and code.

### OTR-019 — Implement structure-aware chunking

**Priority:** P1  
**Description:** Create retrieval chunks without crossing section boundaries or splitting code blocks. Include the heading path in retrieval text.

**Acceptance criteria:**

- [ ] Target size and overlap are configurable.
- [ ] Code blocks remain intact.
- [ ] Every chunk retains book, edition and section metadata.
- [ ] Unit tests cover boundary and oversized-block cases.

### OTR-020 — Build the synchronous ingestion CLI

**Priority:** P1  
**Description:** Create `scripts/ingest_book.py` to validate the manifest, store the raw snapshot, extract structure, chunk content and persist it.

**Acceptance criteria:**

- [ ] Supports a dry-run mode.
- [ ] Re-running the same revision is idempotent.
- [ ] Job counts and failures are recorded.
- [ ] Introduction and Chapters 0–2 ingest end to end.

## Phase 3 — Retrieval

### OTR-021 — Add the Ollama embedding provider

**Priority:** P1  
**Description:** Implement a configurable provider for document and query embeddings with batching, timeouts and dimension validation.

**Acceptance criteria:**

- [ ] Provider-specific code stays behind an interface.
- [ ] Network errors are retried only when safe.
- [ ] Embedding dimensions are validated before storage.
- [ ] Tests use a fake provider.

### OTR-022 — Implement dense and lexical retrieval

**Priority:** P1  
**Description:** Query pgvector similarity and PostgreSQL full-text search independently with book and chapter filters.

**Acceptance criteria:**

- [ ] Both retrievers return a common result type.
- [ ] Results include scores and source metadata.
- [ ] Filters are parameterized safely.
- [ ] Integration tests verify expected ranking.

### OTR-023 — Implement hybrid retrieval with RRF

**Priority:** P1  
**Description:** Fuse dense and lexical rankings using Reciprocal Rank Fusion and attach useful parent-section context.

**Acceptance criteria:**

- [ ] RRF is deterministic and unit-tested.
- [ ] Duplicate chunks are merged correctly.
- [ ] Final result count is configurable.
- [ ] CLI output displays source URLs and ranking information.

## Phase 4 — Grounded answers

### OTR-024 — Implement the Ollama generation provider

**Priority:** P1  
**Description:** Add local model generation behind a provider interface with timeouts, deterministic defaults and structured usage metadata.

**Acceptance criteria:**

- [ ] Model name and temperature are configurable.
- [ ] Provider errors do not leak secrets.
- [ ] Tests use a fake generation provider.
- [ ] No provider call is embedded in retrieval code.

### OTR-025 — Implement strict grounded answering

**Priority:** P1  
**Description:** Build prompts and response structures that answer from retrieved evidence, distinguish unsupported claims and cite exact sections.

**Acceptance criteria:**

- [ ] Responses use `supported`, `partially_supported`, or `unsupported`.
- [ ] Citations are generated from retrieved metadata, not invented by the model.
- [ ] Insufficient evidence produces a clear refusal.
- [ ] Retrieved chunks and latency are returned for inspection.

### OTR-026 — Create the question-answer CLI

**Priority:** P1  
**Description:** Add `scripts/ask_book.py` for asking a selected book a question and printing the answer, support status, citations and retrieval details.

**Acceptance criteria:**

- [ ] Book and retrieval strategy can be selected.
- [ ] Output includes clickable source URLs.
- [ ] Debug output can show retrieved chunks and scores.
- [ ] The first milestone works end to end from the terminal.

## Later phases

### OTR-027 — Build a retrieval evaluation set

**Priority:** P2  
**Description:** Create manually verified questions with known supporting sections and measure Recall@K, MRR and citation accuracy.

### OTR-028 — Add tutor modes

**Priority:** P2  
**Description:** Add Explain, Socratic, Quiz and Code Walkthrough modes over the same deterministic retrieval service.

### OTR-029 — Add FastAPI endpoints

**Priority:** P2  
**Description:** Expose health, books, sections, search, chat and quiz endpoints without duplicating domain logic in route handlers.

### OTR-030 — Validate reuse with Dive into Deep Learning

**Priority:** P2  
**Description:** Ingest the second licensed textbook through the normalized content model and identify only genuinely generalizable loader improvements.

---

# DOING

Move active task cards here. Keep this section limited to one or two tasks.

---

# DONE

### OTR-001 — Create and connect the GitHub repository

**Priority:** P0  
**Description:** Create `JosipTheorem/open-textbook-rag`, clone it locally, and confirm `main` tracks `origin/main`.

**Acceptance criteria:**

- [x] Repository exists on GitHub.
- [x] Local clone points to the correct remote.
- [x] Push and pull work.

### OTR-002 — Create the Python 3.12 environment and requirements

**Priority:** P0  
**Description:** Create `.venv`, add the initial Phase 0/1 dependencies, verify imports, and keep the environment outside Git.

**Acceptance criteria:**

- [x] `.venv` uses Python 3.12.
- [x] `requirements.txt` is committed and pushed.
- [x] `pip check` reports no broken dependencies.
- [x] `.venv` is ignored by Git.

---

## Board maintenance checklist

Before ending a work session:

- [ ] Move completed cards to **DONE**.
- [ ] Update acceptance criteria honestly.
- [ ] Leave unfinished cards in **DOING** with a short progress note.
- [ ] Run `git status`.
- [ ] Commit source changes and this board together when they describe the same work.
- [ ] Push before switching computers.
