# Voice book RAG

A local study assistant that answers questions using passages from an open textbook.
It imports approved Git-hosted Markdown books into PostgreSQL, combines keyword and
vector search, and gives a local Qwen model one LangGraph search tool. Answers cite
the book sections they used. The voice page accepts Croatian or English
speech and reads answers aloud.

The sample source is [Dive into Deep Learning](https://d2l.ai/). Book text, model
weights, and generated embeddings are downloaded or created locally; they are not
included in this repository.

## Requirements

The steps below are for Windows PowerShell, the environment this project has been
tested on. You need Git, Python 3.13, and Docker Desktop. The default Qwen service
requests an NVIDIA GPU; on Windows, Docker Desktop must use its WSL 2 backend with
working GPU support ([Docker's GPU guide](https://docs.docker.com/desktop/features/gpu/)).
Microphone transcription also needs NeMo-Speech.cpp, installed separately below.
No Node.js, hosted LLM, or API key is required.

## Try it

Run these commands from the repository root in PowerShell. The initial image and
model downloads can take a while.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
docker compose up -d --build
docker compose exec ollama-embeddings ollama pull qwen3-embedding:0.6b
docker compose exec ollama-llm ollama pull qwen3.5:9b-q4_K_M
.\.venv\Scripts\python.exe -m alembic -c .\database\alembic.ini upgrade head
.\.venv\Scripts\python.exe .\book_scraper\ingest_book.py --max-files 1
docker compose exec postgres psql -U textbook_rag -d textbook_rag -c "CALL textbook.embed_chunks();"
```

That imports one sample document and embeds its chunks. The final command uses
the default database user/name from `.env.example`; adjust it if you change those
settings. Re-running the importer keeps unchanged documents and embeddings. To
import more approved files, raise `--max-files` and run the embedding command again.

To use another answer model, pull it into `ollama-llm` and set
`OLLAMA_LLM_MODEL` in `.env`; it must support tool calls. The embedding model is
fixed in the SQL and 1024-dimensional database schema. Changing it requires a
migration and re-embedding, not just an `.env` edit.

## Talk to the agent

For microphone transcription, install
[NeMo-Speech.cpp for Windows](https://github.com/NVIDIA/NeMo-Speech.cpp/blob/main/docs/install.md)
and download its model with `nemo-speech pull nemotron-3.5`. Then start these in
two PowerShell windows from the repository root:

```powershell
nemo-speech serve --asr-model nemotron-3.5 --gpu 0 --endpointing
```

```powershell
.\.venv\Scripts\python.exe -m uvicorn voice_app.server:app --host 127.0.0.1 --port 8766
```

Open **http://127.0.0.1:8766**. You can also type on that page without starting
NeMo-Speech.cpp. The voice app loads the LangGraph agent directly and searches
the English book before answering in your language. Supertonic speech weights
download on first use. Stop the services with `Ctrl+C`.

## What installs where?

| File or command | Purpose |
| --- | --- |
| `requirements.txt` | All Python packages for importing books and voice chat. |
| `compose.yaml` | Builds PostgreSQL and starts two Ollama services; named volumes keep database and model data across restarts. |
| `nemo-speech pull nemotron-3.5` | Downloads the separate speech-to-text model for microphone input. |

Python's `pip` does not install Docker images, Ollama models, or NeMo-Speech.cpp.
`.env.example` lists local settings; copy it to `.env` and keep `.env` private.
`docker compose down` stops the containers without deleting their named volumes.

## Project files and license

- [`book_scraper/`](book_scraper/) contains source manifests and the importer.
- [`database/`](database/) contains Docker setup, Alembic migrations, and SQL examples.
- [`textbook_agent/`](textbook_agent/) contains the LangGraph agent and its search tool.
- [`voice_app/`](voice_app/) contains the voice interface.

The original project code is [MIT licensed](LICENSE). Downloaded books and models
retain their own licenses; see [third-party content notes](THIRD_PARTY_CONTENT.md).

Possible next step: download a licensed evaluation dataset, embed it, and
compare this small local model with popular hosted API models on the same
questions and evidence. Use an LLM judge for answer quality, while measuring
retrieval accuracy separately so search failures are not blamed on the model.
