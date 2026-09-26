"""Local-only voice gateway for the existing LangGraph agent."""

from __future__ import annotations

import asyncio
import base64
import io
import json
import os
import re
import wave
from pathlib import Path
from typing import Any

import numpy as np
import websockets
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from langchain_core.messages import AIMessage, HumanMessage
from supertonic import TTS

from textbook_agent.agent import build_agent

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
NEMO_WS = os.getenv(
    "VOICE_ASR_WS", "ws://127.0.0.1:8080/v1/audio/transcriptions/realtime"
)
APP_DIR = Path(__file__).resolve().parent
app = FastAPI(title="Textbook voice")
agent = build_agent()
_tts: TTS | None = None
_tts_lock = asyncio.Lock()


def _get_tts() -> TTS:
    global _tts
    if _tts is None:
        # The ONNX CPU provider is used by the SDK. No PyTorch/CUDA install needed.
        _tts = TTS(model="supertonic-3", auto_download=True, intra_op_num_threads=4)
    return _tts


def _speak(text: str, language: str) -> bytes:
    tts = _get_tts()
    style = tts.get_voice_style("M1")
    audio, _ = tts.synthesize(
        text,
        voice_style=style,
        lang=language,
        total_steps=5,
        speed=1.15,
        max_chunk_length=300,
        silence_duration=0.1,
    )
    samples = np.asarray(audio).reshape(-1)
    pcm = (np.clip(samples, -1, 1) * 32767).astype("<i2").tobytes()
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(tts.sample_rate)
        wav.writeframes(pcm)
    return buffer.getvalue()


def _speech_chunks(text: str, max_length: int = 300) -> list[str]:
    """Speak the first sentence promptly, then batch the rest without truncation."""
    text = re.split(
        r"\n\s*(?:#+\s*)?(?:Sources|Izvori)\b",
        text,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    text = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[`*_#]", "", text)
    sentences = re.split(r"(?<=[.!?;:])\s+", text.strip())
    pieces: list[str] = []
    for sentence in sentences:
        current = ""
        for word in sentence.split():
            if current and len(current) + len(word) + 1 > max_length:
                pieces.append(current)
                current = ""
            current = f"{current} {word}".strip()
        if current:
            pieces.append(current)

    if not pieces:
        return []
    chunks = [pieces[0]]
    for piece in pieces[1:]:
        if len(chunks[-1]) + len(piece) + 1 <= max_length and len(chunks) > 1:
            chunks[-1] += f" {piece}"
        else:
            chunks.append(piece)
    return chunks


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(APP_DIR / "index.html")


@app.get("/capture.js")
async def capture() -> FileResponse:
    return FileResponse(APP_DIR / "capture.js", media_type="text/javascript")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "asr": NEMO_WS}


@app.websocket("/ws")
async def voice_socket(browser: WebSocket) -> None:
    await browser.accept()
    history: list[Any] = []
    asr: Any = None
    asr_task: asyncio.Task[None] | None = None
    answer_task: asyncio.Task[None] | None = None
    language = "auto"

    async def emit(payload: dict[str, Any]) -> None:
        try:
            await browser.send_json(payload)
        except WebSocketDisconnect:
            # A browser tab may close while TTS is still producing a segment.
            pass

    async def answer(question: str) -> None:
        nonlocal history
        if not question.strip():
            await emit({"type": "status", "text": "No speech detected."})
            return
        history.append(HumanMessage(content=question))
        await emit({"type": "user", "text": question})
        await emit({"type": "status", "text": "Searching and answering…"})
        try:
            final: AIMessage | None = None
            async for update in agent.astream({"messages": history}, stream_mode="updates"):
                for node in update.values():
                    for message in node.get("messages", []):
                        if isinstance(message, AIMessage) and not message.tool_calls:
                            final = message
            if final is None:
                raise RuntimeError("The agent returned no answer")
            history.append(final)
            reply = str(final.content)
            await emit({"type": "assistant", "text": reply})
            speech_language = "hr" if language == "hr-HR" else "en"
            if language == "auto":
                speech_language = "hr" if re.search(r"[čćđšžČĆĐŠŽ]", reply) else "en"
            async with _tts_lock:
                for chunk in _speech_chunks(reply):
                    sound = await asyncio.to_thread(_speak, chunk, speech_language)
                    await emit({"type": "audio", "data": base64.b64encode(sound).decode("ascii")})
            await emit({"type": "done"})
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - report service failures to the UI
            await emit({"type": "error", "text": f"Agent or TTS failed: {exc}"})

    async def read_asr(connection: Any) -> None:
        nonlocal answer_task, asr
        partial = ""
        try:
            async for raw in connection:
                if isinstance(raw, bytes):
                    continue
                event = json.loads(raw)
                kind = event.get("type", "")
                if kind.endswith(".delta"):
                    partial += event.get("delta", "")
                    await emit({"type": "partial", "text": partial})
                elif kind.endswith(".completed"):
                    text = event.get("transcript", event.get("text", ""))
                    answer_task = asyncio.create_task(answer(text))
                    break
                elif kind == "error":
                    await emit({"type": "error", "text": str(event.get("error", event))})
        except Exception as exc:  # noqa: BLE001 - report ASR failures to the UI
            await emit({"type": "error", "text": f"ASR failed: {exc}"})
        finally:
            await connection.close()
            asr = None

    try:
        while True:
            packet = await browser.receive()
            if packet["type"] == "websocket.disconnect":
                break
            data = packet.get("bytes")
            if data is not None:
                if asr is not None:
                    await asr.send(data)
                continue
            command = json.loads(packet.get("text") or "{}")
            kind = command.get("type")
            if kind == "start":
                if asr is not None:
                    continue
                language = command.get("language", "auto")
                if language not in {"auto", "hr-HR", "en-US"}:
                    language = "auto"
                try:
                    asr = await websockets.connect(NEMO_WS, max_size=4_000_000)
                    await asr.send(json.dumps({"type": "session.update", "session": {
                        "sample_rate": 16000, "language": language,
                        "endpointing_ms": 550,
                    }}))
                    asr_task = asyncio.create_task(read_asr(asr))
                    await emit({"type": "status", "text": "Listening…"})
                except Exception as exc:  # noqa: BLE001 - report connection failures
                    asr = None
                    await emit({"type": "error", "text": f"Cannot connect to NeMo ASR: {exc}"})
            elif kind == "stop" and asr is not None:
                await asr.send(json.dumps({"type": "input_audio_buffer.commit"}))
                await emit({"type": "status", "text": "Transcribing…"})
            elif kind == "text":
                if answer_task and not answer_task.done():
                    answer_task.cancel()
                answer_task = asyncio.create_task(answer(str(command.get("text", ""))))
            elif kind == "cancel":
                if answer_task and not answer_task.done():
                    answer_task.cancel()
    except WebSocketDisconnect:
        pass
    finally:
        if asr is not None:
            await asr.close()
        if asr_task is not None:
            asr_task.cancel()
        if answer_task is not None:
            answer_task.cancel()
