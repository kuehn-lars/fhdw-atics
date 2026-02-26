"""
api/agents_router.py
────────────────────
NDJSON-Streaming router für alle CrewAI Challenge-Skripte.

Jedes Challenge-Skript konfiguriert:
    CHALLENGE_INPUT = "..."   ← im Skript anpassen
    run_challenge(question)   ← wird mit CHALLENGE_INPUT aufgerufen

Das Frontend schickt KEINEN Input – nur POST ohne Body.
stdout wird live als NDJSON gestreamt (ein JSON-Objekt pro Zeile).

Endpoints:
    POST /agents/challenge1
    POST /agents/challenge2
    POST /agents/challenge3

Output Format (NDJSON – ein JSON pro Zeile):
    {"type": "status", "message": "Starte Challenge: 'Was ist RAG?'"}
    {"type": "log", "text": "Agent Researcher startet..."}
    {"type": "log", "text": "Using tool: Frage das RAG System..."}
    {"type": "result", "answer": "..."}

    Bei Fehler:
    {"type": "error", "message": "..."}
"""
import os

# ── Disable ALL CrewAI / OpenTelemetry / Posthog telemetry ──────────────────
# Must happen BEFORE any `from crewai import ...` (triggered by challenge modules)
os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"
os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["POSTHOG_DISABLED"] = "true"
os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"

import asyncio
import io
import json
import queue
import re
import sys
import threading
import importlib.util

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/agents", tags=["Agents"])

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_WORKSHOPS_DIR = os.path.join(_ROOT, "workshops", "crewai_intro")

# Module-Cache: einmalig laden, nicht bei jedem Request neu
_module_cache: dict = {}

# Regex zum Entfernen von ANSI-Escape-Codes (Farben, Box-Drawing etc.)
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _ndjson(data: dict) -> str:
    """Ein JSON-Objekt + Newline (NDJSON-Format)."""
    return json.dumps(data, ensure_ascii=False) + "\n"


class _QueueWriter(io.TextIOBase):
    """
    Temporärer sys.stdout-Ersatz.
    Jede Zeile → JSON log-Objekt in der Queue.
    Spiegelt auch auf den originalen stdout (uvicorn-Logs bleiben sichtbar).
    """
    def __init__(self, q: queue.Queue, original):
        self._q = q
        self._orig = original

    def write(self, text: str) -> int:
        if text and text.strip():
            clean = _ANSI_RE.sub("", text).rstrip("\n")
            if clean.strip():  # skip empty lines after stripping
                self._q.put(_ndjson({"type": "log", "text": clean}))
        self._orig.write(text)
        return len(text)

    def flush(self):
        self._orig.flush()


def _get_module(filename: str):
    """
    Lädt ein Challenge-Modul – gecacht nach filename.
    Module-Level-Code (get_rag_pipeline etc.) läuft nur beim ersten Aufruf.
    """
    if filename not in _module_cache:
        if _ROOT not in sys.path:
            sys.path.insert(0, _ROOT)

        full_path = os.path.join(_WORKSHOPS_DIR, filename)
        spec = importlib.util.spec_from_file_location(f"_challenge_{filename}", full_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _module_cache[filename] = mod

    return _module_cache[filename]


def _worker(mod, fn_name: str, q: queue.Queue):
    """
    Background-Thread: führt mod.<fn_name>(mod.CHALLENGE_INPUT) aus.
    stdout → Queue (JSON log-Objekte).
    """
    original_stdout = sys.stdout
    sys.stdout = _QueueWriter(q, original_stdout)
    try:
        fn = getattr(mod, fn_name)
        challenge_input = getattr(mod, "CHALLENGE_INPUT", "Keine Frage konfiguriert")
        result = fn(challenge_input)
        q.put(_ndjson({"type": "result", "answer": str(result)}))
    except Exception as exc:
        q.put(_ndjson({"type": "error", "message": str(exc)}))
    finally:
        sys.stdout = original_stdout
        q.put(None)  # Sentinel: Generator stoppt hier


def _make_endpoint(filename: str, fn_name: str = "run_challenge"):
    """Factory: erzeugt einen Route-Handler für eine Challenge-Datei."""

    async def endpoint():
        mod = _get_module(filename)
        challenge_input = getattr(mod, "CHALLENGE_INPUT", "?")

        q: queue.Queue = queue.Queue()
        thread = threading.Thread(target=_worker, args=(mod, fn_name, q), daemon=True)
        thread.start()

        loop = asyncio.get_running_loop()

        async def generator():
            # Erste Zeile: Status mit Challenge-Info
            yield _ndjson({"type": "status", "message": f"Starte Challenge: '{challenge_input}'"})
            while True:
                item = await loop.run_in_executor(None, q.get)
                if item is None:
                    break
                yield item

        return StreamingResponse(
            generator(),
            media_type="application/x-ndjson",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return endpoint


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints  (kein Request-Body – Konfiguration im jeweiligen Skript)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/challenge1", summary="Challenge 1 – Researcher + Writer")
async def challenge1():
    return await _make_endpoint("agents_challenge1.py")()


@router.post("/challenge2", summary="Challenge 2 – Researcher + Writer")
async def challenge2():
    return await _make_endpoint("agents_challenge2.py")()


@router.post("/challenge3", summary="Challenge 3 – Researcher + Writer")
async def challenge3():
    return await _make_endpoint("agents_challenge3.py")()


