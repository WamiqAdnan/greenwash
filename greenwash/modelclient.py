"""The seam every Corpus Case calls instead of talking to Ollama directly.

Two modes, chosen by GREENWASH_MODE:

  replay (default)  Look the prompt up in the case's fixtures. No network, no
                    GPU, deterministic to the byte. This is what the Harness
                    runs and what a judge reproduces.
  record            Call Ollama for real and write the answer into fixtures.

Replay is not a testing convenience — it is what makes a Kill Rate a fact
rather than a sample. A Mutant that survives under replay survived because the
suite is blind, never because the model happened to answer differently.
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.request
from pathlib import Path

DEFAULT_MODEL = "qwen3:8b"
OLLAMA_URL = "http://localhost:11434/api/generate"


class FixtureMiss(RuntimeError):
    """A prompt was asked for in replay mode that has never been recorded."""


def _key(model: str, prompt: str) -> str:
    digest = hashlib.sha256(f"{model}\x00{prompt}".encode()).hexdigest()[:16]
    return f"{model.replace(':', '_')}__{digest}"


def _fixture_dir() -> Path:
    d = os.environ.get("GREENWASH_FIXTURES")
    if not d:
        raise RuntimeError(
            "GREENWASH_FIXTURES is unset. The Harness sets it per Corpus Case; "
            "set it yourself if you are calling a feature module directly."
        )
    return Path(d)


def _call_ollama(model: str, prompt: str) -> str:
    body = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "options": {"temperature": 0, "num_predict": 512},
        }
    ).encode()
    req = urllib.request.Request(
        OLLAMA_URL, data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.load(resp)["response"]


def complete(prompt: str, model: str | None = None) -> str:
    """Answer `prompt`, from fixtures in replay mode or from Ollama in record mode.

    `model` is deliberately overridable: the downgrade Operator works by handing
    a Corpus Case a weaker model, and that only bites if the feature reads the
    model name at call time rather than at import time.
    """
    model = model or os.environ.get("GREENWASH_MODEL", DEFAULT_MODEL)
    mode = os.environ.get("GREENWASH_MODE", "replay")
    path = _fixture_dir() / f"{_key(model, prompt)}.json"

    if mode == "replay":
        if not path.exists():
            raise FixtureMiss(
                f"No fixture for model={model} at {path.name}.\n"
                f"Run: python scripts/record_fixtures.py --case <case>"
            )
        return json.loads(path.read_text())["response"]

    if mode == "record":
        if path.exists():
            return json.loads(path.read_text())["response"]
        response = _call_ollama(model, prompt)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {"model": model, "prompt": prompt, "response": response},
                indent=2,
            )
        )
        return response

    raise RuntimeError(f"GREENWASH_MODE must be replay or record, got {mode!r}")
