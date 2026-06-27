"""Bridge the LLM env contract into ``~/.nanobot/config.json``.

This is the **single source of truth** for that bridge. Verbatim copies live next
to each deploy entrypoint so they keep working even if the installed SDK can't be
imported:

  - ``deploy/_nanobot_config.py``                       (Docker all-in-one)
  - ``runagent-serverless/scripts/_nanobot_config.py``  (baked into the VM image)
  - ``runagent/templates/superbrowser/default/_nanobot_config.py``  (scaffold)

Keep them byte-identical to this file (``diff`` should be empty).

The LLM choice reaches a run as environment variables — set in ``.env`` for local
and Docker, or delivered by runagent-serverless to ``/root/.env`` in the VM::

    LLM_PROVIDER   provider name (openai, anthropic, gemini, groq, …)
    LLM_MODEL      model id (e.g. ``gpt-4o``)
    LLM_API_KEY    the provider API key
    LLM_BASE_URL   optional base URL (custom / OpenAI-compatible endpoints)

A plain ``OPENAI_API_KEY`` / ``ANTHROPIC_API_KEY`` (an older deploy, or a shell
export) is accepted as a fallback.

nanobot, however, reads its model + provider key **only** from
``~/.nanobot/config.json``. Nothing runs ``nanobot onboard`` in the image, so
without this step ``load_config`` returns its built-in defaults (no usable API
key) and the browser agent can't reach any LLM — regardless of what the user
picked. This module merges the env contract into that config file before the
agent constructs nanobot.

Two entry points, same merge:

  - :func:`ensure_nanobot_config` — always (re)writes when an LLM is resolvable.
    Use it where the env is the only source of truth (a fresh VM/container).
  - :func:`bootstrap_nanobot_config` — "onboard wins, ``.env`` bootstraps": only
    writes when an explicit ``LLM_*`` signal is set or no usable config exists
    yet. Use it for the local in-process SDK, so a stray exported provider key
    never clobbers a deliberate ``nanobot onboard``.
"""

from __future__ import annotations

import os

# Casual / dashboard provider names → nanobot registry names
# (see nanobot/providers/registry.py).
_PROVIDER_ALIASES = {
    "google": "gemini",
    "google-gemini": "gemini",
    "googleai": "gemini",
    "qwen": "dashscope",
    "kimi": "moonshot",
}

# Provider → its conventional API-key env var, so a plain OPENAI_API_KEY /
# ANTHROPIC_API_KEY (older deploys, or a shell export) still works when
# LLM_API_KEY isn't set.
_PROVIDER_KEY_ENV = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "groq": "GROQ_API_KEY",
}

# The deliberate runagent LLM contract. A bare OPENAI_API_KEY / ANTHROPIC_API_KEY
# is intentionally NOT in this set: those are often exported globally and must not
# silently override a local `nanobot onboard`.
_EXPLICIT_LLM_ENV = ("LLM_PROVIDER", "LLM_MODEL", "LLM_API_KEY", "LLM_BASE_URL")


def _norm_provider(name: str) -> str:
    name = (name or "").strip().lower()
    return _PROVIDER_ALIASES.get(name, name)


def _resolve() -> dict | None:
    """Pull the LLM config out of the environment, or ``None`` if it's absent."""
    provider = _norm_provider(os.environ.get("LLM_PROVIDER", ""))
    model = (os.environ.get("LLM_MODEL") or "").strip()
    base_url = (os.environ.get("LLM_BASE_URL") or "").strip()
    api_key = (os.environ.get("LLM_API_KEY") or "").strip()

    if not api_key and provider in _PROVIDER_KEY_ENV:
        api_key = (os.environ.get(_PROVIDER_KEY_ENV[provider]) or "").strip()
    if not api_key:
        # Last resort: adopt a conventional key and infer the provider from it.
        for prov, env in (("anthropic", "ANTHROPIC_API_KEY"), ("openai", "OPENAI_API_KEY")):
            val = (os.environ.get(env) or "").strip()
            if val:
                api_key = val
                provider = provider or prov
                break
    if not provider and api_key:
        provider = "anthropic" if os.environ.get("ANTHROPIC_API_KEY") else "openai"
    if not (api_key and provider):
        return None
    return {"provider": provider, "model": model, "api_key": api_key, "base_url": base_url}


def _has_explicit_llm_env() -> bool:
    """True if the deliberate runagent LLM contract is present in the environment.

    A bare ``OPENAI_API_KEY`` / ``ANTHROPIC_API_KEY`` does NOT count — those are
    often exported globally and must not silently override a local onboard.
    """
    return any((os.environ.get(k) or "").strip() for k in _EXPLICIT_LLM_ENV)


def _config_has_usable_provider() -> bool:
    """True if ``~/.nanobot/config.json`` already carries a provider API key."""
    import json

    path = os.path.expanduser("~/.nanobot/config.json")
    if not os.path.exists(path):
        return False
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (ValueError, OSError):
        return False
    providers = data.get("providers") if isinstance(data, dict) else None
    if not isinstance(providers, dict):
        return False
    return any(
        isinstance(cfg, dict) and str(cfg.get("apiKey") or "").strip()
        for cfg in providers.values()
    )


def bootstrap_nanobot_config() -> bool:
    """Local in-process bridge — "onboard wins, ``.env`` bootstraps".

    Merge the LLM env contract into ``~/.nanobot/config.json`` ONLY when:

      - an explicit ``LLM_*`` signal is set (a deliberate choice that overrides a
        prior onboard), or
      - there is no usable config yet (no ``providers.<name>.apiKey``) — first-run
        bootstrap from ``.env`` / the shell.

    Otherwise leave the existing config untouched, so a stray exported provider
    key never clobbers a deliberate ``nanobot onboard``. Returns ``True`` when the
    config was (re)written. Never raises.
    """
    if not (_has_explicit_llm_env() or not _config_has_usable_provider()):
        return False
    return ensure_nanobot_config()


def ensure_nanobot_config() -> bool:
    """Merge the LLM env contract into ``~/.nanobot/config.json`` unconditionally.

    Writes the file directly as JSON (camelCase keys, nanobot's on-disk format)
    rather than going through nanobot's Python API. This keeps it robust across
    the nanobot version split — the deployed image pins ``nanobot-ai`` 0.1.x
    while local dev may run a newer build, and the *file* format is far more
    stable than the internal schema classes. nanobot reads provider keys both
    from ``providers.<name>.apiKey`` and from the provider's conventional env var,
    and the middleware sets both, so the LLM works regardless.

    Idempotent and best-effort: returns ``True`` when the file was (re)written,
    ``False`` when there's nothing to do. Never raises — on failure the agent
    falls back to whatever config already exists.
    """
    info = _resolve()
    if not info:
        return False

    import json

    path = os.path.expanduser("~/.nanobot/config.json")
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)

        # Start from the current file so unrelated settings under ~/.nanobot
        # (and any earlier deploy's tweaks on the persistent disk) survive.
        data: dict = {}
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as fh:
                    loaded = json.load(fh)
                if isinstance(loaded, dict):
                    data = loaded
            except (ValueError, OSError):
                data = {}

        provider = info["provider"]
        agents = data.get("agents")
        if not isinstance(agents, dict):
            agents = {}
            data["agents"] = agents
        defaults = agents.get("defaults")
        if not isinstance(defaults, dict):
            defaults = {}
            agents["defaults"] = defaults
        # Explicit provider => nanobot routes by it; the model stays as the user
        # typed it (the provider impl strips any "provider/" prefix on send).
        defaults["provider"] = provider
        if info["model"]:
            defaults["model"] = info["model"]
        # A leftover preset would shadow the model/provider we just set.
        defaults.pop("modelPreset", None)
        defaults.pop("model_preset", None)

        providers = data.get("providers")
        if not isinstance(providers, dict):
            providers = {}
            data["providers"] = providers
        prov_cfg = providers.get(provider)
        if not isinstance(prov_cfg, dict):
            prov_cfg = {}
        prov_cfg["apiKey"] = info["api_key"]
        if info["base_url"]:
            prov_cfg["apiBase"] = info["base_url"]
        providers[provider] = prov_cfg

        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        os.replace(tmp, path)  # atomic
        return True
    except Exception as exc:  # noqa: BLE001 - never break the agent over config
        try:
            from loguru import logger

            logger.warning("ensure_nanobot_config: could not write nanobot config: {}", exc)
        except Exception:  # noqa: BLE001
            pass
        return False
