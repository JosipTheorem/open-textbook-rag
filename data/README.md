# Local textbook data

The application uses this directory for downloaded and processed textbook files.
The contents are local working data and must not be committed to Git.

- `raw/` holds untouched source snapshots.
- `processed/` holds normalized intermediate files.

The PostgreSQL database lives in a Docker-managed volume. Textbook files remain
here in ordinary folders so they can be inspected without a separate storage
service.
