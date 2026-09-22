"""Import licensed Git-hosted Markdown books into PostgreSQL."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin
from uuid import UUID, uuid4

import yaml
from psycopg import Connection, connect
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPOSITORY_ROOT / "book_sources" / "dive-into-deep-learning.yaml"
DEFAULT_DATABASE_URL = (
    "postgresql://textbook_rag:local-development-only@127.0.0.1:5432/textbook_rag"
)
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
FENCE_PATTERN = re.compile(r"^```\s*([^`]*)$")
IMAGE_PATTERN = re.compile(r"^!\[(?P<caption>[^]]*)]\((?P<target>[^)]+)\)\s*$")
LIST_PATTERN = re.compile(r"^\s*(?:[-*+] |\d+[.)] )")
SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+")


@dataclass(slots=True)
class ContentBlock:
    """One indivisible content element inside a section."""

    block_type: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Section:
    """A Markdown heading and the content owned by that heading."""

    level: int
    title: str
    heading_path: list[str]
    blocks: list[ContentBlock] = field(default_factory=list)


@dataclass(slots=True)
class Chunk:
    """A retrieval unit that never crosses a section boundary."""

    text: str
    word_count: int
    content_types: list[str]


@dataclass(slots=True)
class ParsedDocument:
    """A source file after structure-aware parsing."""

    source_path: str
    title: str
    content_hash: str
    sections: list[Section]


def _clean_heading(value: str) -> str:
    value = re.sub(r"\s*\{[^}]+}\s*$", "", value)
    return value.strip().strip("#").strip()


def parse_markdown(source_path: str, text: str) -> ParsedDocument:
    """Parse headings, prose, lists, figures, equations, and fenced code."""
    sections: list[Section] = []
    heading_stack: dict[int, str] = {}
    current: Section | None = None
    paragraph_lines: list[str] = []
    code_lines: list[str] = []
    equation_lines: list[str] = []
    code_language = ""
    in_code = False
    in_equation = False

    def ensure_section() -> Section:
        nonlocal current
        if current is None:
            current = Section(level=1, title="Document", heading_path=["Document"])
            sections.append(current)
        return current

    def flush_paragraph() -> None:
        if not paragraph_lines:
            return
        stripped = [line.strip() for line in paragraph_lines if line.strip()]
        paragraph_lines.clear()
        if not stripped:
            return
        is_list = all(LIST_PATTERN.match(line) for line in stripped)
        content = "\n".join(stripped) if is_list else " ".join(stripped)
        ensure_section().blocks.append(
            ContentBlock("list" if is_list else "paragraph", content)
        )

    for raw_line in text.splitlines():
        line = raw_line.rstrip()

        if in_code:
            if line.strip().startswith("```"):
                content = "\n".join(code_lines).rstrip()
                ensure_section().blocks.append(
                    ContentBlock("code", content, {"language": code_language})
                )
                code_lines.clear()
                code_language = ""
                in_code = False
            else:
                code_lines.append(line)
            continue

        fence_match = FENCE_PATTERN.match(line.strip())
        if fence_match:
            flush_paragraph()
            in_code = True
            code_language = fence_match.group(1).strip()
            continue

        if in_equation:
            if line.strip() == "$$":
                ensure_section().blocks.append(
                    ContentBlock("equation", "\n".join(equation_lines).strip())
                )
                equation_lines.clear()
                in_equation = False
            else:
                equation_lines.append(line)
            continue

        if line.strip() == "$$":
            flush_paragraph()
            in_equation = True
            continue

        heading_match = HEADING_PATTERN.match(line)
        if heading_match:
            flush_paragraph()
            level = len(heading_match.group(1))
            title = _clean_heading(heading_match.group(2))
            for old_level in [item for item in heading_stack if item >= level]:
                del heading_stack[old_level]
            heading_stack[level] = title
            heading_path = [heading_stack[item] for item in sorted(heading_stack)]
            current = Section(level=level, title=title, heading_path=heading_path)
            sections.append(current)
            continue

        image_match = IMAGE_PATTERN.match(line.strip())
        if image_match:
            flush_paragraph()
            caption = image_match.group("caption").strip()
            if caption:
                ensure_section().blocks.append(
                    ContentBlock(
                        "figure_caption",
                        caption,
                        {"target": image_match.group("target").strip()},
                    )
                )
            continue

        stripped_line = line.strip()
        if not stripped_line:
            flush_paragraph()
            continue
        if stripped_line.startswith((":label:", ":begin_tab:", ":end_tab:")):
            continue
        if stripped_line.startswith("<!--") and stripped_line.endswith("-->"):
            continue
        paragraph_lines.append(line)

    flush_paragraph()
    if in_code and code_lines:
        ensure_section().blocks.append(
            ContentBlock("code", "\n".join(code_lines).rstrip(), {"language": code_language})
        )
    if in_equation and equation_lines:
        ensure_section().blocks.append(
            ContentBlock("equation", "\n".join(equation_lines).strip())
        )

    title = next((section.title for section in sections if section.level == 1), Path(source_path).stem)
    return ParsedDocument(
        source_path=source_path,
        title=title,
        content_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        sections=sections,
    )


def _split_long_prose(text: str, target_words: int) -> list[str]:
    if len(text.split()) <= target_words:
        return [text]
    sentences = SENTENCE_SPLIT_PATTERN.split(text)
    pieces: list[str] = []
    current: list[str] = []
    current_words = 0
    for sentence in sentences:
        words = sentence.split()
        if len(words) > target_words:
            if current:
                pieces.append(" ".join(current))
                current = []
                current_words = 0
            pieces.extend(
                " ".join(words[start : start + target_words])
                for start in range(0, len(words), target_words)
            )
            continue
        if current and current_words + len(words) > target_words:
            pieces.append(" ".join(current))
            current = []
            current_words = 0
        current.append(sentence)
        current_words += len(words)
    if current:
        pieces.append(" ".join(current))
    return pieces


def chunk_section(
    section: Section,
    target_words: int = 350,
    overlap_words: int = 60,
) -> list[Chunk]:
    """Create chunks without crossing a heading or splitting code/equations."""
    if target_words <= 0 or overlap_words < 0 or overlap_words >= target_words:
        raise ValueError("Chunk sizes must satisfy 0 <= overlap < target.")

    pieces: list[tuple[str, str]] = []
    for block in section.blocks:
        if block.block_type in {"code", "equation"}:
            block_pieces = [block.text]
        else:
            block_pieces = _split_long_prose(block.text, target_words)
        pieces.extend((block.block_type, piece) for piece in block_pieces if piece.strip())

    chunks: list[Chunk] = []
    current: list[tuple[str, str]] = []
    current_words = 0

    def emit() -> None:
        if not current:
            return
        heading = " > ".join(section.heading_path)
        body = "\n\n".join(piece for _, piece in current)
        text = f"Section: {heading}\n\n{body}".strip()
        chunks.append(
            Chunk(
                text=text,
                word_count=len(text.split()),
                content_types=sorted({kind for kind, _ in current}),
            )
        )

    for piece in pieces:
        piece_words = len(piece[1].split())
        if current and current_words + piece_words > target_words:
            emit()
            overlap: list[tuple[str, str]] = []
            overlap_count = 0
            for previous in reversed(current):
                previous_words = len(previous[1].split())
                if previous[0] in {"code", "equation"}:
                    continue
                if overlap_count + previous_words > overlap_words:
                    break
                overlap.insert(0, previous)
                overlap_count += previous_words
            current = overlap
            current_words = overlap_count
        current.append(piece)
        current_words += piece_words
    emit()
    return chunks


def load_manifest(source: str) -> dict[str, Any]:
    """Load a manifest, or resolve a known licensed source URL to its manifest."""
    if source.startswith(("https://", "http://")):
        manifest_path = DEFAULT_MANIFEST
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        expected = str(manifest["source_url"]).removesuffix(".git").rstrip("/")
        received = source.removesuffix(".git").rstrip("/")
        if received != expected:
            raise ValueError(
                "Unknown URL. Add a reviewed source manifest before importing this book."
            )
    else:
        manifest_path = Path(source)
        if not manifest_path.is_absolute():
            manifest_path = REPOSITORY_ROOT / manifest_path
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))

    required = {
        "id",
        "title",
        "authors",
        "source_type",
        "source_url",
        "canonical_url",
        "license_identifier",
        "license_url",
        "attribution",
        "authorized_for_ingestion",
        "snapshot_directory",
        "include_patterns",
    }
    missing = sorted(required - set(manifest))
    if missing:
        raise ValueError(f"Manifest is missing: {', '.join(missing)}")
    if manifest["authorized_for_ingestion"] is not True:
        raise ValueError("The source is not marked as authorized for ingestion.")
    if manifest["source_type"] != "git_markdown":
        raise ValueError("This first importer supports git_markdown sources only.")
    return manifest


def _run_git(arguments: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def ensure_source(manifest: dict[str, Any]) -> tuple[Path, str]:
    """Clone the approved source if needed and return its exact revision."""
    source_url = str(manifest["source_url"])
    if not source_url.startswith("https://"):
        raise ValueError("Only HTTPS Git sources are accepted.")
    snapshot = (REPOSITORY_ROOT / str(manifest["snapshot_directory"])).resolve()
    raw_root = (REPOSITORY_ROOT / "data" / "raw").resolve()
    if raw_root not in snapshot.parents:
        raise ValueError("Source snapshots must stay inside data/raw/.")

    if not (snapshot / ".git").exists():
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        _run_git(
            [
                "clone",
                "--depth",
                "1",
                "--filter=blob:none",
                "--sparse",
                source_url,
                str(snapshot),
            ]
        )
        roots = sorted(
            {
                str(pattern).split("/", maxsplit=1)[0]
                for pattern in manifest["include_patterns"]
            }
        )
        _run_git(["sparse-checkout", "set", *roots], cwd=snapshot)

    revision = _run_git(["rev-parse", "HEAD"], cwd=snapshot)
    return snapshot, revision


def collect_documents(
    snapshot: Path,
    manifest: dict[str, Any],
    max_files: int,
) -> list[ParsedDocument]:
    """Read only manifest-approved Markdown paths from the local snapshot."""
    candidates: set[Path] = set()
    for pattern in manifest["include_patterns"]:
        candidates.update(snapshot.glob(str(pattern)))

    documents: list[ParsedDocument] = []
    for path in sorted(candidates)[:max_files]:
        resolved = path.resolve()
        if snapshot not in resolved.parents or not resolved.is_file():
            continue
        relative_path = resolved.relative_to(snapshot).as_posix()
        text = resolved.read_text(encoding="utf-8")
        documents.append(parse_markdown(relative_path, text))
    if not documents:
        raise ValueError("No Markdown documents matched the approved manifest patterns.")
    return documents


def _database_dsn(explicit_url: str | None) -> str:
    url = explicit_url or os.getenv("DATABASE_URL") or DEFAULT_DATABASE_URL
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def _source_urls(
    manifest: dict[str, Any], revision: str, source_path: str
) -> tuple[str, str]:
    repository = str(manifest["source_url"]).removesuffix(".git")
    source_url = f"{repository}/blob/{revision}/{quote(source_path, safe='/')}"
    html_path = str(Path(source_path).with_suffix(".html")).replace("\\", "/")
    canonical_url = urljoin(str(manifest["canonical_url"]).rstrip("/") + "/", html_path)
    return source_url, canonical_url


def _insert_book(conn: Connection[Any], manifest: dict[str, Any]) -> UUID:
    row = conn.execute(
        """
        INSERT INTO textbook.books (
            id, slug, title, authors, canonical_url, license_identifier,
            license_url, attribution
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (slug) DO UPDATE SET
            title = EXCLUDED.title,
            authors = EXCLUDED.authors,
            canonical_url = EXCLUDED.canonical_url,
            license_identifier = EXCLUDED.license_identifier,
            license_url = EXCLUDED.license_url,
            attribution = EXCLUDED.attribution,
            updated_at = CURRENT_TIMESTAMP
        RETURNING id
        """,
        (
            uuid4(),
            manifest["id"],
            manifest["title"],
            Jsonb(manifest["authors"]),
            manifest["canonical_url"],
            manifest["license_identifier"],
            manifest["license_url"],
            manifest["attribution"],
        ),
    ).fetchone()
    assert row is not None
    return row["id"]


def store_documents(
    manifest: dict[str, Any],
    revision: str,
    documents: list[ParsedDocument],
    database_url: str | None,
    target_words: int,
    overlap_words: int,
) -> dict[str, int]:
    """Replace one exact source revision with a deterministic structured import."""
    run_id = uuid4()
    aggregate_hash = hashlib.sha256(
        "".join(document.content_hash for document in documents).encode("ascii")
    ).hexdigest()
    totals = {"documents": 0, "sections": 0, "blocks": 0, "chunks": 0}

    with connect(_database_dsn(database_url), autocommit=True, row_factory=dict_row) as conn:
        conn.execute(
            """
            INSERT INTO textbook.ingestion_runs (
                id, status, source_url, source_revision
            ) VALUES (%s, 'running', %s, %s)
            """,
            (run_id, manifest["source_url"], revision),
        )
        try:
            with conn.transaction():
                book_id = _insert_book(conn, manifest)
                conn.execute(
                    "DELETE FROM textbook.editions WHERE book_id = %s AND source_revision = %s",
                    (book_id, revision),
                )
                edition_id = uuid4()
                conn.execute(
                    """
                    INSERT INTO textbook.editions (
                        id, book_id, source_type, source_url, source_revision, content_hash
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        edition_id,
                        book_id,
                        manifest["source_type"],
                        manifest["source_url"],
                        revision,
                        aggregate_hash,
                    ),
                )

                for document_ordinal, document in enumerate(documents, start=1):
                    document_id = uuid4()
                    source_url, canonical_url = _source_urls(
                        manifest, revision, document.source_path
                    )
                    conn.execute(
                        """
                        INSERT INTO textbook.source_documents (
                            id, edition_id, source_path, source_url, canonical_url,
                            title, ordinal, content_hash
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            document_id,
                            edition_id,
                            document.source_path,
                            source_url,
                            canonical_url,
                            document.title,
                            document_ordinal,
                            document.content_hash,
                        ),
                    )
                    totals["documents"] += 1
                    parents: dict[int, UUID] = {}

                    for section_ordinal, section in enumerate(document.sections, start=1):
                        parent_levels = [level for level in parents if level < section.level]
                        parent_id = parents[max(parent_levels)] if parent_levels else None
                        for level in [level for level in parents if level >= section.level]:
                            del parents[level]
                        section_id = uuid4()
                        parents[section.level] = section_id
                        conn.execute(
                            """
                            INSERT INTO textbook.sections (
                                id, document_id, parent_id, level, ordinal, title, heading_path
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                section_id,
                                document_id,
                                parent_id,
                                section.level,
                                section_ordinal,
                                section.title,
                                Jsonb(section.heading_path),
                            ),
                        )
                        totals["sections"] += 1

                        for block_ordinal, block in enumerate(section.blocks, start=1):
                            conn.execute(
                                """
                                INSERT INTO textbook.content_blocks (
                                    id, section_id, ordinal, block_type, text, metadata
                                ) VALUES (%s, %s, %s, %s, %s, %s)
                                """,
                                (
                                    uuid4(),
                                    section_id,
                                    block_ordinal,
                                    block.block_type,
                                    block.text,
                                    Jsonb(block.metadata),
                                ),
                            )
                            totals["blocks"] += 1

                        for chunk_index, chunk in enumerate(
                            chunk_section(section, target_words, overlap_words)
                        ):
                            conn.execute(
                                """
                                INSERT INTO textbook.chunks (
                                    id, section_id, chunk_index, text, word_count,
                                    content_types, heading_path, source_url, content_hash
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                """,
                                (
                                    uuid4(),
                                    section_id,
                                    chunk_index,
                                    chunk.text,
                                    chunk.word_count,
                                    chunk.content_types,
                                    Jsonb(section.heading_path),
                                    canonical_url,
                                    hashlib.sha256(chunk.text.encode("utf-8")).hexdigest(),
                                ),
                            )
                            totals["chunks"] += 1

                conn.execute(
                    """
                    UPDATE textbook.ingestion_runs
                    SET book_id = %s,
                        status = 'completed',
                        finished_at = CURRENT_TIMESTAMP,
                        documents_created = %s,
                        sections_created = %s,
                        blocks_created = %s,
                        chunks_created = %s
                    WHERE id = %s
                    """,
                    (
                        book_id,
                        totals["documents"],
                        totals["sections"],
                        totals["blocks"],
                        totals["chunks"],
                        run_id,
                    ),
                )
        except Exception as error:
            conn.execute(
                """
                UPDATE textbook.ingestion_runs
                SET status = 'failed', finished_at = CURRENT_TIMESTAMP, error = %s
                WHERE id = %s
                """,
                (str(error), run_id),
            )
            raise
    return totals


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import an approved Git-hosted Markdown textbook into PostgreSQL."
    )
    parser.add_argument(
        "source",
        nargs="?",
        default=str(DEFAULT_MANIFEST.relative_to(REPOSITORY_ROOT)),
        help="Approved manifest path or a URL already represented by that manifest.",
    )
    parser.add_argument("--max-files", type=int, default=1)
    parser.add_argument("--target-words", type=int, default=350)
    parser.add_argument("--overlap-words", type=int, default=60)
    parser.add_argument("--database-url", default=None)
    return parser


def main() -> int:
    args = build_argument_parser().parse_args()
    if args.max_files <= 0:
        raise ValueError("--max-files must be positive.")
    manifest = load_manifest(args.source)
    snapshot, revision = ensure_source(manifest)
    documents = collect_documents(snapshot, manifest, args.max_files)
    totals = store_documents(
        manifest,
        revision,
        documents,
        args.database_url,
        args.target_words,
        args.overlap_words,
    )
    print(f"Imported: {manifest['title']}")
    print(f"Source revision: {revision}")
    print(
        "Stored: "
        f"{totals['documents']} document, "
        f"{totals['sections']} sections, "
        f"{totals['blocks']} blocks, "
        f"{totals['chunks']} chunks"
    )
    print("Embeddings: not generated yet")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Import failed: {error}", file=sys.stderr)
        sys.exit(1)
