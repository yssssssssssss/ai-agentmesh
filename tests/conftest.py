from __future__ import annotations

import os
import tempfile
from pathlib import Path

TEST_DB_PATH = Path(tempfile.gettempdir()) / "agentmesh-pytest.sqlite3"
if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()

os.environ["AGENTMESH_DB_PATH"] = str(TEST_DB_PATH)

for key in (
    "AI_API_URL",
    "AI_API_KEY",
    "AI_MODEL",
    "AI_API_STYLE",
    "AGENTMESH_LLM_BASE_URL",
    "AGENTMESH_LLM_API_KEY",
    "AGENTMESH_LLM_MODEL",
    "AGENTMESH_LLM_API_STYLE",
):
    os.environ[key] = ""
