from scripts.ingest_book import chunk_section, parse_markdown

SAMPLE = """# Example Book

Opening paragraph with enough context to keep.

## First Section

This explanation belongs only to the first section.

```python
print("code remains whole")
```

## Second Section

* first item
* second item
"""


def test_parser_preserves_heading_hierarchy_and_code() -> None:
    document = parse_markdown("chapter/index.md", SAMPLE)

    assert [section.heading_path for section in document.sections] == [
        ["Example Book"],
        ["Example Book", "First Section"],
        ["Example Book", "Second Section"],
    ]
    assert document.sections[1].blocks[1].block_type == "code"
    assert document.sections[1].blocks[1].text == 'print("code remains whole")'
    assert document.sections[2].blocks[0].block_type == "list"


def test_chunks_never_cross_section_boundaries() -> None:
    document = parse_markdown("chapter/index.md", SAMPLE)

    first_chunks = chunk_section(document.sections[1], target_words=20, overlap_words=5)
    second_chunks = chunk_section(document.sections[2], target_words=20, overlap_words=5)

    assert all("Second Section" not in chunk.text for chunk in first_chunks)
    assert all("First Section" not in chunk.text for chunk in second_chunks)
    assert any('print("code remains whole")' in chunk.text for chunk in first_chunks)
