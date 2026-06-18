# Oxygen-CLI Smoke Test

Date: 2026-06-18

## Goal

Verify whether AgentMesh can use Oxygen-CLI as a real internal data provider for `research_agent` and `data_agent`.

## Local Runtime

- Project-local O2 binary: `.venv/bin/o2`
- O2 version: `o2 0.0.5`
- O2 registry login: available and logged in
- Installed related CLIs found on this machine:
  - `metasearch`
  - `o2-kb`
  - `oxygen-comment`
  - `bdp-copilot`

Do not expose raw O2 login payloads in frontend APIs. The O2 status adapter redacts cookie, token, password, secret, credential, and key fields.

## Commands Verified

```bash
.venv/bin/o2 --version
.venv/bin/o2 login --status --json
.venv/bin/o2 list --agent-json --limit 20
.venv/bin/o2 launch metasearch --json schema
.venv/bin/o2 launch metasearch --json smoke
.venv/bin/o2 launch metasearch --json doctor
.venv/bin/o2 launch o2-kb config list --json
.venv/bin/o2 launch oxygen-comment --json doctor
.venv/bin/o2 launch bdp-copilot --help
```

## Results

- O2 registry status: pass.
- O2 tool discovery: pass.
- `metasearch` installed: pass.
- `metasearch` schema: pass.
- `metasearch` local smoke: pass.
- `metasearch` real search: blocked by missing JD access token.
- `o2-kb` real recall: blocked by missing initialization. It requires `o2-kb init`.
- `oxygen-comment` doctor: pass for environment/permissions, blocked for credentials.
- `oxygen-comment` real query readiness: blocked by missing credentials/cookie.
- `bdp-copilot` runtime: pass for command availability and help output; real JSON query still needs a `find-tables --json-output` smoke test after Oxygen login reuse is confirmed.

## Blocking Items

### metasearch

`metasearch doctor` reports:

- Token file does not exist: `~/.config/metasearch/token.json`
- `JD_METASEARCH_ACCESS_TOKEN` is not set

To unblock real search:

```bash
.venv/bin/o2 launch metasearch auth-url
.venv/bin/o2 launch metasearch login
```

The login command prompts for a JD access token. Do not commit or paste the token into project files.

After login, validate with:

```bash
.venv/bin/o2 launch metasearch --json doctor
.venv/bin/o2 launch metasearch --json search "华为手机" --output json
```

### Current 2026-06-18 smoke result

- `.venv/bin/o2 --version` returns `o2 0.0.5`.
- `.venv/bin/o2 login --status --json` shows the registry login is already available and logged in.
- `.venv/bin/o2 launch metasearch --json doctor` still reports no local token file and no `JD_METASEARCH_ACCESS_TOKEN`.
- `.venv/bin/o2 launch o2-kb config list --json` still reports uninitialized config.
- `.venv/bin/o2 launch oxygen-comment --json doctor` still reports missing credentials.
- `.venv/bin/o2 launch bdp-copilot --help` shows the runtime and commands are installed: `find-tables`, `code-generate`, `code-rewrite`, and `diagnosis`.
- The project O2 status adapter reports `ready` only for registry login and `needs_config` for the remaining setup checks.

### o2-kb

`o2-kb` reports that config has not been initialized.

To unblock recall:

```bash
o2-kb init
o2-kb config list
o2-kb recall list "618 家电会场" --json
```

### oxygen-comment

`oxygen-comment doctor` reports missing credentials.

To unblock real queries:

```bash
oxygen-comment doctor --json
oxygen-comment config set credentials.cookie '<cookie>'
```

Prefer a supported corporate login reuse flow if available. Do not commit cookies into project files.

### bdp-copilot

`bdp-copilot --help` confirms that the runtime is installed. It still needs a real JSON smoke test:

```bash
.venv/bin/o2 launch bdp-copilot --json-output find-tables "618 会场入口点击率"
```

If it cannot reuse the Oxygen login state, follow its help output and configure only local environment variables such as `BDP_TOKEN`, `BDP_APP_ID`, or `BDP_ERP`. Do not commit those values.

## AgentMesh Configuration For Retest

Use the project-local O2 binary:

```bash
export AGENTMESH_O2_COMMAND=.venv/bin/o2
export AGENTMESH_O2_RESEARCH_ENABLED=true
export AGENTMESH_O2_RESEARCH_CLI=metasearch
```

For data connector retest:

```bash
export AGENTMESH_O2_DATA_ENABLED=true
export AGENTMESH_O2_DATA_CLI=metasearch
```

Then run:

```bash
.venv/bin/python eval/run_eval.py
```

And manually verify a chat query that should route to `request_external_research`.

## Current Conclusion

AgentMesh has a valid O2 integration boundary and the local O2 runtime is present. The real internal data smoke test is not fully passed yet because tool-level credentials are missing for real network queries.

## Product Integration Update

AgentMesh now exposes O2 setup checks in the O2 status payload and Agent page:

- O2 registry login
- metasearch token
- o2-kb init
- oxygen-comment credentials
- Browser Bridge daemon/extension readiness

These checks intentionally report missing credentials as `needs_config` instead of hiding the failure behind a generic mock fallback.

## Fallback Strategy

- `research_agent` tries enabled real providers first: O2 and external Web.
- A real research provider is considered successful only when it returns sources.
- If all real research providers fail or return no sources, AgentMesh falls back to `MockAcquisitionAgent` and records provider diagnostics in metadata.
- `data_agent` tries `o2_cli` before `local_metrics` when the connector is registered.
- If the real data connector fails or returns no records, AgentMesh falls back to `local_metrics` and records fallback diagnostics.
