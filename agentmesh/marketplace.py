"""Autonomous collaboration market — background workers.

agent-1 (publisher): periodically publishes each user's MARKETPLACE_SIGNAL to the BBS.
Gated by a global master switch (mirrors the other worker env flags). The step function
``publish_all_signals`` is the tested unit; the asyncio loop is a thin wrapper, following
the auto-post / research-dispatch worker convention (loop untested, step tested).
"""

from __future__ import annotations

import asyncio
import contextlib
import os

from agentmesh.agents import PersonalAgent
from agentmesh.models import now_utc
from agentmesh.seed import list_users
from agentmesh.store import SQLiteStore, store


def _bool_env(name: str) -> bool:
    return os.getenv(name, "").lower() in {"1", "true", "yes", "on"}


def _positive_int_env(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except ValueError:
        return default


# Master switch for the whole autonomous market (off by default).
MARKET_ENABLED = _bool_env("AGENTMESH_MARKET_ENABLED")
MARKET_PUBLISH_INTERVAL_SECONDS = _positive_int_env("AGENTMESH_MARKET_PUBLISH_INTERVAL_SECONDS", 300)
MARKET_SCOUT_INTERVAL_SECONDS = _positive_int_env("AGENTMESH_MARKET_SCOUT_INTERVAL_SECONDS", 300)

publish_worker_task: asyncio.Task | None = None
publish_worker_state: dict[str, object] = {
    "enabled": MARKET_ENABLED,
    "interval_seconds": MARKET_PUBLISH_INTERVAL_SECONDS,
    "running": False,
    "last_run_at": None,
    "last_published": 0,
    "last_error": None,
}


def publish_all_signals(repository: SQLiteStore) -> int:
    """Publish a MARKETPLACE_SIGNAL for every user that has source material. Returns the count.

    This is the step function the publisher worker drives each tick; it's the tested seam.
    """
    agent = PersonalAgent(repository)
    published = 0
    for user in list_users(repository):
        if agent.publish_marketplace_signal(user) is not None:
            published += 1
    return published


async def publish_worker_loop() -> None:
    while True:
        await asyncio.sleep(MARKET_PUBLISH_INTERVAL_SECONDS)
        publish_worker_state["last_run_at"] = now_utc().isoformat()
        try:
            published = publish_all_signals(store)
            publish_worker_state["last_published"] = published
            publish_worker_state["last_error"] = None
        except Exception as error:  # pragma: no cover - defensive worker boundary
            publish_worker_state["last_error"] = str(error)


async def start_market_publish_worker() -> None:
    global publish_worker_task
    if MARKET_ENABLED and (publish_worker_task is None or publish_worker_task.done()):
        publish_worker_task = asyncio.create_task(publish_worker_loop())
        publish_worker_state["running"] = True


async def stop_market_publish_worker() -> None:
    global publish_worker_task
    if publish_worker_task is not None:
        publish_worker_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await publish_worker_task
        publish_worker_task = None
    publish_worker_state["running"] = False


# --- agent-2: scout ---

scout_worker_task: asyncio.Task | None = None
scout_worker_state: dict[str, object] = {
    "enabled": MARKET_ENABLED,
    "interval_seconds": MARKET_SCOUT_INTERVAL_SECONDS,
    "running": False,
    "last_run_at": None,
    "last_triggered": 0,
    "last_error": None,
}


def scout_all(repository: SQLiteStore) -> int:
    """Run every user's scout; return the total number of delegated answers triggered.

    This is the step function the scout worker drives each tick; it's the tested seam.
    """
    agent = PersonalAgent(repository)
    triggered = 0
    for user in list_users(repository):
        triggered += len(agent.scout_and_match(user))
    return triggered


async def scout_worker_loop() -> None:
    while True:
        await asyncio.sleep(MARKET_SCOUT_INTERVAL_SECONDS)
        scout_worker_state["last_run_at"] = now_utc().isoformat()
        try:
            triggered = scout_all(store)
            scout_worker_state["last_triggered"] = triggered
            scout_worker_state["last_error"] = None
        except Exception as error:  # pragma: no cover - defensive worker boundary
            scout_worker_state["last_error"] = str(error)


async def start_market_scout_worker() -> None:
    global scout_worker_task
    if MARKET_ENABLED and (scout_worker_task is None or scout_worker_task.done()):
        scout_worker_task = asyncio.create_task(scout_worker_loop())
        scout_worker_state["running"] = True


async def stop_market_scout_worker() -> None:
    global scout_worker_task
    if scout_worker_task is not None:
        scout_worker_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await scout_worker_task
        scout_worker_task = None
    scout_worker_state["running"] = False
