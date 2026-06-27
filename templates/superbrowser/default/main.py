"""RunAgent SuperBrowser — serverless agent entrypoint.

This module exposes the agent's ``run`` / ``run_stream`` entrypoints. The same
file is used in three places (kept byte-identical): baked into the serverless VM
at /root/main.py, the all-in-one Docker container's deploy/main.py, and the
``runagent init --from-template superbrowser/default`` scaffold. The vsock runner
/ ``runagent serve`` loads it and invokes ``run`` per request. It drives the
superbrowser engine started on 127.0.0.1:3100, with per-user cookies/profiles
under ~/.superbrowser and nanobot state under ~/.nanobot (persisted on the
/persistent disk in the VM).

An LLM key (OPENAI_API_KEY / ANTHROPIC_API_KEY, or the LLM_PROVIDER / LLM_MODEL /
LLM_API_KEY contract) must be present in the environment — set it in this
directory's .env (uploaded by `runagent deploy`, loaded by docker-compose, or
written to the VM's /root/.env). See .env.example. The nanobot brain is then
configured from that env by ``ensure_nanobot_config`` (the _nanobot_config bridge).
"""
import asyncio
import os
import time
import urllib.request

ENGINE_URL = os.environ.get("SUPERBROWSER_URL", "http://127.0.0.1:3100")

_sb = None
_config_ready = False


def _ensure_nanobot_config() -> None:
    """Write the env's LLM choice into ~/.nanobot/config.json once.

    runagent-serverless / .env deliver the LLM config as env vars (LLM_PROVIDER /
    LLM_MODEL / LLM_API_KEY / LLM_BASE_URL); nanobot reads it only from its config
    file. The ``_nanobot_config`` bridge reconciles the two. Prefer the installed
    SDK's copy (the single source of truth); fall back to the sibling baked next
    to this file. Runs once per process, before the first nanobot build.
    """
    global _config_ready
    if _config_ready:
        return
    try:
        try:
            from runagent_superbrowser._nanobot_config import ensure_nanobot_config
        except Exception:  # noqa: BLE001 - fall back to the sibling copy
            from _nanobot_config import ensure_nanobot_config

        ensure_nanobot_config()
    except Exception:  # noqa: BLE001 - best effort; never block a run
        pass
    _config_ready = True


def _wait_for_engine(timeout: float = 90.0) -> None:
    """Block until the local engine answers /health (covers cold boot)."""
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
        # Imported lazily so module load (at vsock-runner start) never races the
        # not-yet-ready engine.
        from runagent_superbrowser import SuperBrowser

        _ensure_nanobot_config()
        _wait_for_engine()
        # model is also written into ~/.nanobot/config.json by _ensure_nanobot_config;
        # passing it here covers the in-process model-override path on newer SDKs.
        try:
            _sb = SuperBrowser(server_url=ENGINE_URL, model=os.environ.get("LLM_MODEL") or None)
        except TypeError:
            # Older SDK without a model kwarg.
            _sb = SuperBrowser(server_url=ENGINE_URL)
    return _sb


def _has_llm_credentials() -> bool:
    return bool(
        os.environ.get("LLM_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY")
        or os.path.exists(os.path.expanduser("~/.nanobot/config.json"))
    )


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

    result = _client().run(
        task,
        mode=mode,
        url=url,
        output_schema=output_schema,
        timeout=timeout,
    )

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


async def run_stream(task, mode="auto", url=None, output_schema=None, timeout=None):
    """Stream a browser task as step-level events, ending with a result event.

    Yields JSON-serializable dicts (see ``SuperBrowser.astream``): progress events
    (classification / status / thinking / tool / message) followed by a final
    {"type": "result", ...} matching the ``run`` payload. The vsock runner
    serializes each yielded item and frames the stream over the WebSocket back to
    the SDK.

    Degrades gracefully: if the installed runagent_superbrowser SDK predates
    streaming (no ``astream``), this runs the task and yields a single result.
    """
    if not _has_llm_credentials():
        yield {
            "type": "result",
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
        return

    # _client() blocks while waiting for the engine; keep it off the event loop.
    loop = asyncio.get_running_loop()
    sb = await loop.run_in_executor(None, _client)

    if hasattr(sb, "astream"):
        async for event in sb.astream(
            task, mode=mode, url=url, output_schema=output_schema, timeout=timeout
        ):
            yield event
    else:
        # Old SDK without streaming: degrade to a single result event.
        result = await loop.run_in_executor(
            None,
            lambda: run(task, mode=mode, url=url, output_schema=output_schema, timeout=timeout),
        )
        result = dict(result)
        result["type"] = "result"
        yield result
