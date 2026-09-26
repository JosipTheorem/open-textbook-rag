# Book scraper files

- [ingest_book.py](ingest_book.py) — downloads approved Git books and imports their Markdown into PostgreSQL.
- [sources/](sources/) — book source manifests; currently [Dive into Deep Learning](sources/dive-into-deep-learning.yaml).
- [data/raw/](data/raw/) — local downloaded book files, ignored by Git.
- [data/processed/](data/processed/) — empty placeholder for intermediate files.
