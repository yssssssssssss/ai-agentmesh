from __future__ import annotations

from agentmesh.models import Agent
from agentmesh.seed import list_agents
from agentmesh.store import SQLiteStore


def list_public_agents(repository: SQLiteStore) -> list[Agent]:
    return [agent for agent in list_agents(repository) if agent.agent_type != "personal"]
