"""
Phase 0 — OpenAI Connectivity Check
===================================
Verifies that the configured OpenAI endpoint and API key are working.

Run:
  python check_openai.py
"""

from __future__ import annotations

import asyncio

from app.core.config import OPENAI_BASE_URL, OPENAI_MODEL, OPENAI_TIMEOUT
from app.infrastructure.openai_client import OpenAIClient, OpenAIClientError


async def check_openai_connection() -> bool:
    print("\n" + "=" * 60)
    print("  OPENAI CONNECTIVITY CHECK")
    print("=" * 60)
    print(f"\n  Base URL   : {OPENAI_BASE_URL}")
    print(f"  Model      : {OPENAI_MODEL}")
    print(f"  Timeout    : {OPENAI_TIMEOUT}s")

    client = OpenAIClient()

    reachable = await client.ping()
    if not reachable:
        print("\n  ✗  OpenAI API is unreachable or API key is missing/invalid.")
        return False

    print("\n  ✓  OpenAI API reachable")

    try:
        models = await client.list_models()
    except OpenAIClientError as exc:
        print(f"  ✗  Could not list models: {exc}")
        return False

    print(f"  ✓  Retrieved {len(models)} model(s)")
    if OPENAI_MODEL in models:
        print(f"  ✓  Configured model '{OPENAI_MODEL}' is available")
    else:
        print(f"  !  Configured model '{OPENAI_MODEL}' not found in list")

    return True


if __name__ == "__main__":
    ok = asyncio.run(check_openai_connection())
    raise SystemExit(0 if ok else 1)
