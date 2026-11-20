"""LLM backends. A backend is any callable (messages, schema) -> reply text.

Real participant days only ever go to `OllamaBackend`, a model running on your own machine
(docs/decisions.md, Oct 16). Tests use `FakeBackend`, so CI never calls a model.

Setup on your laptop:
    brew install ollama        # or download from ollama.com
    ollama serve               # leave running in its own terminal
    ollama pull llama3.1:8b    # about 5 GB, once (8 GB Macs: llama3.2:3b, 2 GB)

Settings (.env or environment): OLLAMA_MODEL (default llama3.1:8b), OLLAMA_URL
(default http://localhost:11434).
"""

import os
from collections.abc import Callable

import requests

Backend = Callable[[list[dict], dict], str]


class OllamaBackend:
    def __init__(self, model: str | None = None, url: str | None = None, seed: int = 0):
        self.model = model or os.environ.get("OLLAMA_MODEL", "llama3.1:8b")
        self.url = (url or os.environ.get("OLLAMA_URL", "http://localhost:11434")).rstrip("/")
        self.seed = seed

    def __call__(self, messages: list[dict], schema: dict) -> str:
        try:
            resp = requests.post(f"{self.url}/api/chat", timeout=600, json={
                "model": self.model, "messages": messages, "format": schema, "stream": False,
                # temperature 0 + a fixed seed: the same prompt gives the same plan
                "options": {"temperature": 0, "seed": self.seed},
            })
        except requests.ConnectionError as e:
            raise RuntimeError(f"Can't reach Ollama at {self.url}. Start it with `ollama serve` "
                               f"in another terminal.") from e
        if resp.status_code == 404:
            raise RuntimeError(f"Model {self.model} isn't downloaded. Run `ollama pull "
                               f"{self.model}`.")
        resp.raise_for_status()
        return resp.json()["message"]["content"]

    def __repr__(self) -> str:
        return f"ollama:{self.model}"


class FakeBackend:
    """Returns canned replies in order (the last one repeats). Records every prompt."""

    def __init__(self, *replies: str):
        self.replies = list(replies)
        self.calls: list[list[dict]] = []

    def __call__(self, messages: list[dict], schema: dict) -> str:
        self.calls.append(messages)
        return self.replies[min(len(self.calls), len(self.replies)) - 1]

    def __repr__(self) -> str:
        return "fake"
