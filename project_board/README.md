# Local project board

This board is a visual, Git-synced replacement for `TASK_BOARD.md`.

## Start it

From the repository root:

```powershell
python .\project_board\run_board.py
```

If the virtual environment is not activated:

```powershell
.\.venv\Scripts\python.exe .\project_board\run_board.py
```

The board opens at:

```text
http://127.0.0.1:8765/project_board/
```

Use **Create task** at the top of the board to add your own task. Give it a clear
title, explain what needs to be done, and list how you will know it is finished.
Opening an existing card lets you edit or delete it. Drag cards between **To do**,
**Doing**, and **Done** as the work progresses.

## How persistence works

Moving, adding, editing, or deleting a task updates `project_board/tasks.json` through the local Python server. The server listens only on `127.0.0.1` by default and writes the file atomically.

After changing tasks:

```powershell
git diff -- project_board/tasks.json
git add project_board/tasks.json
git commit -m "Update project board"
git push
```

On another computer:

```powershell
git pull
python .\project_board\run_board.py
```

Stop the server with `Ctrl+C` before pulling remote task-board changes.

## Files

- `index.html` — semantic page structure
- `board.css` — responsive visual design
- `board.js` — drag/drop, filters, editing, and saving
- `tasks.json` — the only frequently changing Git-tracked board data
- `run_board.py` — dependency-free local server and persistence API

Do not open `index.html` directly from File Explorer. Browsers do not allow a static file to silently rewrite `tasks.json`; run the local server instead.
