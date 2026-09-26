# Open Textbook RAG Lab

A local-first study platform for turning openly licensed or user-authorized
technical textbooks into grounded AI learning companions.

## Local database

Docker runs PostgreSQL with pgvector plus a private CPU-only Ollama service for
embeddings. Original and processed textbook files stay in the ignored `data/`
folders. Build and start the services from the repository root:

```powershell
docker compose up -d --build
```

The first start downloads the container image and can take a few minutes. Check
its status:

```powershell
docker compose ps
```

The default local database settings are documented in `.env.example`. To use
your own settings, copy `.env.example` to `.env` and edit the copy before
starting the database. Git ignores `.env`.

Stop the services without deleting their data:

```powershell
docker compose down
```

Start it again with `docker compose up -d`; database data is kept in a named
Docker volume.

## Embeddings and hybrid search

Download the embedding model once on each computer. Its files remain in a
Docker volume and are not committed to Git:

```powershell
docker compose exec ollama-embeddings ollama pull qwen3-embedding:0.6b
```

After importing textbook chunks and applying all migrations, generate every
missing embedding in DBeaver:

```sql
CALL textbook.embed_chunks();
```

The embedding service runs on the CPU so the RTX GPU remains available for the
local LLM. Search needs only the question and desired result count:

```sql
SELECT *
FROM textbook.search_chunks_hybrid('What is machine learning?', 5);
```

See `database/embed_and_search.sql` for checks and readable examples.

## Local LangGraph textbook assistant

The answer-generating model runs in a separate GPU-enabled Ollama container so
the private CPU-only embedding service remains isolated. Start the services and
download the model once:

```powershell
docker compose up -d
docker compose exec ollama-llm ollama pull qwen3.5:9b-q4_K_M
```

For the browser chat UI, start the LangGraph server in one PowerShell window:

```powershell
.\.venv\Scripts\langgraph.exe dev --no-browser
```

Then start the frontend in a second PowerShell window:

```powershell
cd .\textbook-chat
pnpm dev
```

Open `http://localhost:3000`. The frontend is preconfigured for the local graph
named `agent` at `http://localhost:2024`; no LangSmith key is needed for this
local chat UI. The frontend is an ignored local checkout of the official
`langchain-ai/agent-chat-ui` repository rather than duplicated application code.

On a new computer, install the frontend once:

```powershell
winget install --id OpenJS.NodeJS.LTS --exact
npm install --global pnpm@10.5.1
git clone https://github.com/langchain-ai/agent-chat-ui.git textbook-chat
Copy-Item .\textbook-chat\.env.example .\textbook-chat\.env
cd .\textbook-chat
pnpm install
```

The LangGraph agent has exactly one tool: the database-owned
`textbook.search_chunks_hybrid` function. It must retrieve evidence before
answering and includes the source section and URL in its response. Configuration
is available in `.env.example`; the default model endpoint is private to this
computer at `127.0.0.1:11435`.

## Local voice chat (Croatian and English)

Voice is an input/output layer around the existing `textbook_agent.agent.build_agent()`
graph. It does not add another LLM or another retrieval tool. The browser sends
16 kHz microphone audio to NeMo-Speech.cpp's streaming Nemotron ASR; the final
transcript goes to the existing LangGraph/Qwen/hybrid-search agent; Supertonic 3
speaks the answer on CPU. The separate voice page keeps the ignored upstream
Agent Chat UI checkout untouched. Conversation state lives in the voice page's
WebSocket session; refreshing it starts a new conversation.

One-time Windows installation:

```powershell
& ([scriptblock]::Create((curl.exe -L --silent https://raw.githubusercontent.com/NVIDIA/NeMo-Speech.cpp/main/scripts/install.ps1 | Out-String))) -Backend cuda -BinaryOnly
& "$env:LOCALAPPDATA\Programs\NeMoSpeech\bin\nemo-speech.exe" pull nemotron-3.5
.\.venv\Scripts\python.exe -m pip install -r requirements-voice.txt
```

Start Docker first. Then run these in two separate PowerShell windows from the
repository root (the first command keeps the ASR model loaded):

```powershell
& "$env:LOCALAPPDATA\Programs\NeMoSpeech\bin\nemo-speech.exe" serve --asr-model nemotron-3.5 --gpu 0 --endpointing
```

```powershell
.\.venv\Scripts\python.exe -m uvicorn voice_app.server:app --host 127.0.0.1 --port 8766
```

Open `http://127.0.0.1:8766`, allow microphone access, choose Auto, Hrvatski,
or English, then click **Start talking** and **Stop / send**. You can type in
the same page, too. On first use Supertonic downloads its ONNX weights into
the local Hugging Face cache; subsequent runs reuse them. No CUDA toolkit or
PyTorch installation is required for this setup. If Nemotron's Croatian
transcription is not accurate enough, its ASR is isolated behind `VOICE_ASR_WS`
so it can be changed without changing the agent.

Voice source files are in `voice_app/`; `server.py` bridges ASR, agent and TTS,
`capture.js` downsamples browser audio, and `index.html` is the local UI.

## Database versions

Alembic records database-structure changes in Git. Apply every migration that
has not yet run on the current computer:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Check the installed database version:

```powershell
.\.venv\Scripts\python.exe -m alembic current
```

The authoritative history is in `migrations/versions/`. The generated
`database/schema.sql` file provides the equivalent readable PostgreSQL DDL and
must not be edited manually.

## Import a licensed textbook sample

The first source is the official Git repository for *Dive into Deep Learning*,
licensed under CC BY-SA 4.0. Import one Introduction document from the approved
source manifest:

```powershell
.\.venv\Scripts\python.exe .\scripts\ingest_book.py `
    https://github.com/d2l-ai/d2l-en `
    --max-files 1
```

The importer records the exact Git revision and license, preserves the heading
hierarchy, stores paragraphs/code/equations as typed blocks, and creates chunks
that never cross section boundaries. Re-running the same revision replaces its
structured content instead of duplicating it. Downloaded source files remain in
ignored `data/raw/` storage.

This stage deliberately leaves `textbook.chunks.embedding` empty. Run
`CALL textbook.embed_chunks();` after inspecting the imported chunks.

## Project board

Run the local visual project board from the repository root:

```powershell
.\.venv\Scripts\python.exe .\project_board\run_board.py
```

The board opens automatically at:

```text
http://127.0.0.1:8765/project_board/
```

Task changes are saved to `project_board/tasks.json`, so they can be committed
and synchronized through Git. Stop the server with `Ctrl+C`.
