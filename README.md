# Open Textbook RAG Lab

A local-first study platform for turning openly licensed or user-authorized
technical textbooks into grounded AI learning companions.

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
