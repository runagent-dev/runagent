"""SuperBrowser serverless agent entrypoint.

The vsock runner loads this module and exposes ``run`` as the ``run`` entrypoint,
invoked per request. It drives the superbrowser engine that the VM starts on
127.0.0.1:3100, with per-user cookies/profiles persisted under ~/.superbrowser
and nanobot state under ~/.nanobot (both on the /persistent disk).

An LLM key (OPENAI_API_KEY or ANTHROPIC_API_KEY, plus LLM_MODEL) must be set in
this project's .env at deploy time — `runagent deploy` uploads it and the engine
writes it to /root/.env in the VM. See .env.example.
"""
import os
import time
import urllib.request

ENGINE_URL = os.environ.get("SUPERBROWSER_URL", "http://127.0.0.1:3100")

_sb = None


def _has_llm_credentials() -> bool:
    return bool(
        os.environ.get("OPENAI_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY")
        or os.path.exists(os.path.expanduser("~/.nanobot/config.json"))
    )


def _wait_for_engine(timeout: float = 90.0) -> None:
    deadline = time.time() + timeout
    last_err = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{ENGINE_URL}/health", timeout=3) as resp:
                if resp.status == 200:
                    return
        except Exception as exc:  # noqa: BLE001 - engine not up yet
            last_err = exc
        time.sleep(1.0)
    raise RuntimeError(f"superbrowser engine not ready at {ENGINE_URL}: {last_err}")


def _client():
    global _sb
    if _sb is None:
        from runagent_superbrowser import SuperBrowser

        _wait_for_engine()
        _sb = SuperBrowser(server_url=ENGINE_URL)
    return _sb


def run(task, mode="auto", url=None, output_schema=None, timeout=None):
    """Run a browser task and return a JSON-serializable RunResult dict."""
    if not _has_llm_credentials():
        return {
            "text": "",
            "success": False,
            "data": None,
            "error": (
                "No LLM credentials found. Set OPENAI_API_KEY or ANTHROPIC_API_KEY "
                "(plus LLM_MODEL) in the agent's .env at deploy time."
            ),
            "task_id": None,
            "mode": mode,
            "classification": None,
        }

    result = _client().run(task, mode=mode, url=url, output_schema=output_schema, timeout=timeout)

    data = getattr(result, "data", None)
    if hasattr(data, "model_dump"):
        data = data.model_dump()

    return {
        "text": getattr(result, "text", "") or "",
        "success": bool(getattr(result, "success", False)),
        "data": data,
        "error": getattr(result, "error", None),
        "task_id": getattr(result, "task_id", None),
        "mode": getattr(result, "mode", mode),
        "classification": getattr(result, "classification", None),
    }
