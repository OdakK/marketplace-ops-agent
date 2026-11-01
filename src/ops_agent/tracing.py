"""Optional Langfuse tracing: enabled when LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are set."""

from __future__ import annotations

import os


def callbacks() -> list:
    if not (os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY")):
        return []
    try:
        from langfuse.langchain import CallbackHandler
    except ImportError:
        print("langfuse is not installed: run `uv sync --extra tracing` to enable tracing")
        return []
    return [CallbackHandler()]
