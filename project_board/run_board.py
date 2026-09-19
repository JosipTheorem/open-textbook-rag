"""Serve the local project board and persist task changes to tasks.json."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import webbrowser
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

MAX_REQUEST_BYTES = 2 * 1024 * 1024
ALLOWED_STATUSES = {"todo", "doing", "done"}
ALLOWED_PRIORITIES = {"P0", "P1", "P2"}


def validate_board(payload: Any) -> dict[str, Any]:
    """Validate the persisted board shape before replacing the tracked file."""
    if not isinstance(payload, dict):
        raise ValueError("The board must be a JSON object.")

    tasks = payload.get("tasks")
    if not isinstance(tasks, list):
        raise ValueError("The board must contain a tasks array.")

    seen_ids: set[str] = set()
    for position, task in enumerate(tasks, start=1):
        if not isinstance(task, dict):
            raise ValueError(f"Task {position} must be an object.")

        task_id = task.get("id")
        if not isinstance(task_id, str) or not task_id.strip():
            raise ValueError(f"Task {position} has an invalid ID.")
        if task_id in seen_ids:
            raise ValueError(f"Duplicate task ID: {task_id}")
        seen_ids.add(task_id)

        if task.get("status") not in ALLOWED_STATUSES:
            raise ValueError(f"Task {task_id} has an invalid status.")
        if task.get("priority") not in ALLOWED_PRIORITIES:
            raise ValueError(f"Task {task_id} has an invalid priority.")

        for field in ("title", "phase", "description", "notes"):
            if not isinstance(task.get(field, ""), str):
                raise ValueError(f"Task {task_id} field '{field}' must be text.")
        for field in ("acceptance_criteria", "labels"):
            value = task.get(field)
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                raise ValueError(f"Task {task_id} field '{field}' must be a text array.")
        if not isinstance(task.get("order"), (int, float)):
            raise ValueError(f"Task {task_id} has an invalid order.")

    payload["version"] = 1
    return payload


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    """Replace tasks.json atomically so an interrupted save cannot truncate it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=".tasks-",
        suffix=".json.tmp",
        text=True,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def create_handler(repository_root: Path, tasks_path: Path) -> type[SimpleHTTPRequestHandler]:
    class ProjectBoardHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=str(repository_root), **kwargs)

        def do_GET(self) -> None:  # noqa: N802
            route = urlparse(self.path).path
            if route == "/":
                self.send_response(HTTPStatus.FOUND)
                self.send_header("Location", "/project_board/")
                self.end_headers()
                return
            if route == "/api/tasks":
                self._send_tasks()
                return
            super().do_GET()

        def do_PUT(self) -> None:  # noqa: N802
            if urlparse(self.path).path != "/api/tasks":
                self.send_error(HTTPStatus.NOT_FOUND)
                return

            try:
                content_length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self.send_error(HTTPStatus.BAD_REQUEST, "Invalid Content-Length")
                return

            if content_length <= 0 or content_length > MAX_REQUEST_BYTES:
                self.send_error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Invalid request size")
                return

            try:
                raw_payload = self.rfile.read(content_length)
                payload = json.loads(raw_payload.decode("utf-8"))
                validated = validate_board(payload)
                atomic_write_json(tasks_path, validated)
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
                self.send_error(HTTPStatus.BAD_REQUEST, str(error))
                return
            except OSError as error:
                self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, f"Could not save board: {error}")
                return

            self.send_response(HTTPStatus.NO_CONTENT)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

        def _send_tasks(self) -> None:
            try:
                payload = validate_board(json.loads(tasks_path.read_text(encoding="utf-8")))
                encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            except (OSError, json.JSONDecodeError, ValueError) as error:
                self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, f"Could not load board: {error}")
                return

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(encoded)

        def end_headers(self) -> None:
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self' data:; base-uri 'none'; frame-ancestors 'none'")
            super().end_headers()

        def log_message(self, message_format: str, *args: Any) -> None:
            print(f"[board] {self.address_string()} — {message_format % args}")

    return ProjectBoardHandler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local Open Textbook RAG task board.")
    parser.add_argument("--host", default="127.0.0.1", help="Listening host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="Listening port (default: 8765)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open the browser automatically")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repository_root = Path(__file__).resolve().parents[1]
    tasks_path = repository_root / "project_board" / "tasks.json"
    handler = create_handler(repository_root, tasks_path)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    url = f"http://{args.host}:{args.port}/project_board/"

    print(f"Open Textbook RAG project board: {url}")
    print(f"Saving changes to: {tasks_path}")
    print("Press Ctrl+C to stop.")

    if not args.no_browser:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping project board.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
