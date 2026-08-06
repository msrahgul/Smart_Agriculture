"""
llm_client.py – Thin wrapper around a local Ollama server.

Optimised for low-latency responses:
  • Two model tiers:
      ROUTER_MODEL  (0.5b) – picks which tool to call; only needs valid JSON output
      PROSE_MODEL   (1.5b) – formats the final farmer-friendly answer; supports streaming
  • keep_alive=300 keeps models hot in memory/VRAM across chat turns
  • num_predict capped low for the routing call (128) so it never over-generates
  • Streaming generator exposed for the SSE endpoint in app.py
"""
from __future__ import annotations

import json
import requests

OLLAMA_URL     = "http://localhost:11434/api/chat"
ROUTER_MODEL   = "qwen2.5:0.5b-instruct"   # tiny, fast: just outputs a JSON tool call
PROSE_MODEL    = "qwen2.5:1.5b-instruct"   # better prose for final answer
DEFAULT_TIMEOUT = 120                        # seconds; 0.5b should reply in < 10s on CPU


class OllamaClient:
    def __init__(
        self,
        model: str = ROUTER_MODEL,
        base_url: str = OLLAMA_URL,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        self.model   = model
        self.base_url = base_url
        self.timeout  = timeout

    # ── non-streaming call (used for routing / tool-arg extraction) ──────
    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.0,
        stop: list[str] | None = None,
        num_predict: int = 256,
        format_json: bool = False,
    ) -> str:
        """
        Returns the full assistant reply as a string.
        Low temperature + num_predict=256 keeps routing fast.
        """
        options: dict = {
            "temperature": temperature,
            "num_predict": num_predict,
        }
        if stop:
            options["stop"] = stop

        payload: dict = {
            "model":      self.model,
            "messages":   messages,
            "stream":     False,
            "keep_alive": 300,   # keep model loaded for 5 minutes between requests
            "options":    options,
        }
        if format_json:
            payload["format"] = "json"   # Ollama forces valid JSON output

        try:
            resp = requests.post(self.base_url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(
                f"Could not reach Ollama at {self.base_url}. "
                f"Is `ollama serve` running and is '{self.model}' pulled? "
                f"Detail: {e}"
            ) from e

        data = resp.json()
        return data.get("message", {}).get("content", "")

    # ── streaming call (used for the final prose answer) ─────────────────
    def chat_stream(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        num_predict: int = 512,
    ):
        """
        Generator that yields each text token as it arrives from Ollama.
        Intended for use with Flask's stream_with_context / Response.
        """
        payload = {
            "model":      self.model,
            "messages":   messages,
            "stream":     True,
            "keep_alive": 300,
            "options": {
                "temperature": temperature,
                "num_predict": num_predict,
            },
        }
        try:
            with requests.post(
                self.base_url, json=payload,
                timeout=self.timeout, stream=True,
            ) as resp:
                resp.raise_for_status()
                for raw_line in resp.iter_lines():
                    if not raw_line:
                        continue
                    try:
                        chunk = json.loads(raw_line)
                    except json.JSONDecodeError:
                        continue
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        yield token
                    if chunk.get("done"):
                        break
        except requests.exceptions.RequestException as e:
            raise RuntimeError(
                f"Ollama streaming error: {e}"
            ) from e


# ── shared singleton instances ────────────────────────────────────────────
router_llm = OllamaClient(model=ROUTER_MODEL)
prose_llm  = OllamaClient(model=PROSE_MODEL)


def extract_json_block(text: str) -> dict | None:
    """
    Local models wrap JSON in prose / markdown fences.
    Pull out the first {...} block and parse it defensively.
    """
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start : i + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    return None
    return None
