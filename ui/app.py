"""app.py — thin Flask server for the demo UI (map + chat on System B).

Routes:
  GET  /            -> the page (Pyvis map + chat panel)
  GET  /graph.html  -> the standalone Pyvis map (swap this one file when viz delivers)
  POST /ask         -> {question} -> the UI contract (queries the real System B)
  GET  /ask_stream  -> SSE: streams B's tool-call events live, then the final contract

The server stays thin: it routes and delegates "calling B" to backend.py. It never executes
any action — B only proposes; the UI only displays.
"""

from __future__ import annotations

import json
import queue
import threading
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_from_directory

from . import backend

UI_DIR = Path(__file__).resolve().parent

app = Flask(__name__, template_folder=str(UI_DIR / "templates"), static_folder=str(UI_DIR / "static"))


@app.get("/")
def index():
    # The colleague's animated canvas viz + integrated chat (its chat now calls /ask).
    return send_from_directory(UI_DIR / "templates", "ontology-graph.dc.html")


# The viz page loads `./support.js` and `./graph_data.js` (relative to "/"), and also does a
# dynamic import('./graph_data.js'). Serve both at the root paths it expects, from ui/static/.
@app.get("/support.js")
def support_js():
    return send_from_directory(UI_DIR / "static", "support.js")


@app.get("/graph_data.js")
def graph_data_js():
    return send_from_directory(UI_DIR / "static", "graph_data.js")


@app.post("/ask")
def ask():
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"error": "missing question"}), 400
    contract = backend.answer_for_ui(question)
    return jsonify(contract)


@app.get("/ask_stream")
def ask_stream():
    """SSE: live tool-call events (logs visibles, jury criterion #1) then final contract.

    B's `answer_async(on_event=...)` emits one event per tool call plus a final result. We
    run that async coroutine in a worker thread and drain its events through a queue, so the
    sync Flask generator can yield them as `data: {...}` lines. Falls back gracefully to the
    mock (no events, just the final contract) when UI_MOCK=1.
    """
    question = (request.args.get("question") or "").strip()
    if not question:
        return jsonify({"error": "missing question"}), 400

    events: queue.Queue = queue.Queue()
    _DONE = object()

    def worker():
        import asyncio
        import os

        try:
            if os.environ.get("UI_MOCK") == "1":
                contract = backend.answer_for_ui(question)
                for entry in contract.get("tool_trace", []):
                    events.put({"type": "tool_call", **entry})
                events.put({"type": "result", "contract": contract})
            else:
                from system_b.agent import answer_async

                def on_event(ev):
                    events.put(ev)

                asyncio.run(answer_async(question, on_event=on_event))
        except Exception as exc:  # surface failures to the client instead of hanging
            events.put({"type": "error", "message": str(exc)})
        finally:
            events.put(_DONE)

    threading.Thread(target=worker, daemon=True).start()

    def stream():
        while True:
            ev = events.get()
            if ev is _DONE:
                break
            yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"

    return Response(stream(), mimetype="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


if __name__ == "__main__":
    # threaded=True so a slow /ask (~35 s on real B) doesn't block /graph.html or the page.
    app.run(host="127.0.0.1", port=5000, debug=True, threaded=True)
