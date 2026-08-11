# AgentMesh React Complete Replacement Stage 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `app.html` with the React UI while preserving every currently implemented AgentMesh user and admin capability.

**Architecture:** FastAPI remains the only business truth. React uses generated OpenAPI types, a single HTTP client, TanStack Query, feature modules, and browser-level verification. The old UI stays available until every vertical slice passes parity checks, then the root route switches to React and the legacy file is removed.

**Tech Stack:** Python 3.12+, FastAPI, Pydantic, SQLiteStore, React 18, TypeScript 5.6, Vite 5, Tailwind 3, TanStack Query, openapi-typescript, Playwright.

## Global Constraints

- Keep FastAPI and SQLite as the business and persistence seam.
- Do not add PostgreSQL, vector search, SSE, WebSocket, DesignOS, meeting audio, contribution redemption, or plugin-market work.
- Natural chat remains private; explicit `$` skills continue through `POST /api/chat/messages`.
- React never reproduces permission, visibility, risk, memory-promotion, task-owner, or workflow rules.
- All API URLs remain relative `/api`; development uses a Vite proxy and production uses FastAPI same-origin hosting.
- Do not migrate hard-coded credentials, static demo conversations, fallback skill registries, timer-based fake generation, or handler-less controls.
- Every phase must keep either the old UI or the migrated React slice usable.
- Backend verification: `.venv/bin/python -m pytest` and `.venv/bin/ruff check .`.
- Frontend verification: `npm run build` and focused Playwright flows at 390px, 768px, and 1512px.

---

## File Map

### Backend

- `agentmesh/models.py`: response permissions, chat-thread detail, task detail DTOs.
- `agentmesh/permissions.py`: resolved global capabilities.
- `agentmesh/store.py`: user-scoped thread, activity, audit, and lookup helpers.
- `agentmesh/routes/chat.py`: thread list and detail endpoints.
- `agentmesh/routes/blackboard.py`: visible task detail and object authorization.
- `agentmesh/routes/market.py`: authenticated board/status reads.
- `agentmesh/routes/memory.py`: safe team-memory creation and action maps.
- `agentmesh/routes/documents.py`: uploader/admin read visibility.
- `agentmesh/routes/workspace.py`: activity, audit, and private-search scoping.
- `agentmesh/routes/users.py`: workspace-safe directory projection.
- `agentmesh/routes/agents.py`: own/public/admin Agent scoping and bootstrap capabilities.
- `agentmesh/routes/inbox.py`: idempotent Brief confirmation.
- `agentmesh/app.py`: Vite asset hosting, SPA routes, final cutover.

### Frontend

- `agentmesh-demo/src/app/`: providers, router, login gate, error boundary.
- `agentmesh-demo/src/api/`: generated types and the single HTTP seam.
- `agentmesh-demo/src/features/`: auth, digital-self, workspace, knowledge, collaboration, admin modules.
- `agentmesh-demo/src/state/ui/`: Toast and overlay-only state.
- `agentmesh-demo/src/components/ui/`: accessible primitives.
- `agentmesh-demo/e2e/`: real-browser user flows.

---

### Task 1: Harden Backend Visibility and Expose Capabilities

**Files:**
- Modify: `agentmesh/models.py:778-886`
- Modify: `agentmesh/permissions.py:7-90`
- Modify: `agentmesh/routes/market.py:29-113`
- Modify: `agentmesh/routes/memory.py:68-85,242-259`
- Modify: `agentmesh/routes/documents.py:67-82,139-162`
- Modify: `agentmesh/routes/workspace.py:35-86`
- Modify: `agentmesh/routes/users.py:36-38`
- Modify: `agentmesh/routes/agents.py:95-108`
- Modify: `agentmesh/routes/inbox.py:89-135`
- Test: `tests/test_frontend_contracts.py`

**Interfaces:**
- Consumes: `has_permission(user, action, rules)`, existing `current_user`, existing visibility helpers.
- Produces: `BootstrapState.capabilities: list[str]`, response-level `allowed_actions`, scoped list/read behavior.

- [ ] **Step 1: Write failing contract tests**

```python
from fastapi.testclient import TestClient

from agentmesh.app import app
from agentmesh.models import ChatMessage, ChatRole, ChatThread, Scope
from agentmesh.seed import ADMIN, TEAM_LEAD, USER
from agentmesh.store import store
from tests.test_chat_flow import authenticated_client, clear_store


def test_market_board_requires_authentication() -> None:
    clear_store()
    assert TestClient(app).get("/api/market/board").status_code == 401


def test_private_search_never_returns_another_users_thread() -> None:
    clear_store()
    other = ChatThread(
        workspace_id=USER.workspace_id,
        project_id=USER.default_project_id,
        user_id=TEAM_LEAD.id,
        title="other-private",
    )
    store.add_chat_thread(other)
    store.add_chat_message(
        ChatMessage(thread_id=other.id, role=ChatRole.USER, content="跨用户私聊标记", scope=Scope.PRIVATE)
    )
    response = authenticated_client(USER.id).get(
        "/api/search", params={"q": "跨用户私聊标记", "visibility": "personal"}
    )
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_non_admin_cannot_create_accepted_team_memory() -> None:
    clear_store()
    response = authenticated_client(USER.id).post(
        "/api/memory",
        json={"title": "unsafe", "summary": "unsafe", "memory_type": "note", "scope": "team_accepted"},
    )
    assert response.status_code == 403


def test_document_detail_hides_other_users_document() -> None:
    clear_store()
    owner = authenticated_client(TEAM_LEAD.id)
    document_id = owner.post(
        "/api/documents/upload",
        files={"file": ("private.txt", b"private body", "text/plain")},
    ).json()["item"]["id"]
    assert authenticated_client(USER.id).get(f"/api/documents/{document_id}").status_code == 404


def test_bootstrap_returns_resolved_capabilities() -> None:
    clear_store()
    assert "accept_team_memory" not in authenticated_client(USER.id).get("/api/bootstrap").json()["capabilities"]
    assert "accept_team_memory" in authenticated_client(TEAM_LEAD.id).get("/api/bootstrap").json()["capabilities"]
    assert "manage_users" in authenticated_client(ADMIN.id).get("/api/bootstrap").json()["capabilities"]
```

- [ ] **Step 2: Run tests and confirm the current leaks**

Run: `.venv/bin/python -m pytest tests/test_frontend_contracts.py -v`

Expected: FAIL because market board is anonymous, private chat search is not owner-filtered, team-accepted creation is allowed, document reads are global, and bootstrap lacks capabilities.

- [ ] **Step 3: Add response permission fields and capability resolution**

```python
# agentmesh/models.py
class ItemResponse(BaseModel):
    item: Any
    allowed_actions: list[str] = Field(default_factory=list)


class ItemsResponse(BaseModel):
    items: list[Any]
    allowed_actions: dict[str, list[str]] = Field(default_factory=dict)


class PaginatedResponse(BaseModel):
    items: list[Any]
    total: int
    page: int
    page_size: int
    has_next: bool
    allowed_actions: dict[str, list[str]] = Field(default_factory=dict)


class BootstrapState(BaseModel):
    workspace: Workspace
    project: Project
    user: User
    users: list[User]
    teams: list[Team] = Field(default_factory=list)
    team_memberships: list[TeamMembership] = Field(default_factory=list)
    agents: list[Agent]
    metrics: BootstrapMetrics
    capabilities: list[str] = Field(default_factory=list)

class MemoryOverviewResponse(BaseModel):
    project_id: str
    sections: dict[str, list[MemoryItem | UserMemoryItem]]
    counts: dict[str, int]
    daily_summary_worker: dict[str, Any]
```

```python
# agentmesh/permissions.py
ACTION_MANAGE_USERS = "manage_users"
ACTION_MANAGE_WORKSPACES = "manage_workspaces"
ACTION_MANAGE_RISK_POLICIES = "manage_risk_policies"
ACTION_SYNC_O2 = "sync_o2"


def capabilities_for_user(user: User, rules: list[PermissionPolicyRule]) -> list[str]:
    actions = {
        ACTION_ACCEPT_TEAM_MEMORY,
        ACTION_MANAGE_PUBLIC_AGENT,
        ACTION_MANAGE_TEAM_MEMBERSHIP,
    }
    if is_admin(user):
        actions.update({ACTION_MANAGE_USERS, ACTION_MANAGE_WORKSPACES, ACTION_MANAGE_RISK_POLICIES, ACTION_SYNC_O2})
    return sorted(action for action in actions if has_permission(user, action, rules) or is_admin(user))
```

Set explicit response models on the typed reads:

```python
@router.get("/activity/today", response_model=ActivityTodayResponse)
def activity_today(user: User = Depends(current_user)) -> ActivityTodayResponse: ...


@router.get("/audit", response_model=AuditListResponse)
def audit_events(...) -> AuditListResponse: ...


@router.get("/overview", response_model=MemoryOverviewResponse)
def memory_overview(...) -> MemoryOverviewResponse: ...
```

Update each affected route so server-side checks run before serialization. Use 404 for hidden documents, 403 for forbidden commands, and include object action maps without changing the existing `item` or `items` shape.

- [ ] **Step 4: Run focused and full backend checks**

Run: `.venv/bin/python -m pytest tests/test_frontend_contracts.py tests/test_permissions.py tests/test_chat_flow.py -v`

Expected: PASS.

Run: `.venv/bin/ruff check agentmesh tests/test_frontend_contracts.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agentmesh/models.py agentmesh/permissions.py agentmesh/routes tests/test_frontend_contracts.py
git commit -m "Harden frontend API visibility"
```

### Task 2: Add User-Scoped Thread and Task Read Interfaces

**Files:**
- Modify: `agentmesh/models.py:261-269,868-886`
- Modify: `agentmesh/store.py:270-276,443-450,529-530`
- Modify: `agentmesh/routes/chat.py:20-40`
- Modify: `agentmesh/routes/blackboard.py:236-299`
- Test: `tests/test_frontend_contracts.py`

**Interfaces:**
- Consumes: authenticated `User`, `task_visible_to_user`, `post_visible_to_user`.
- Produces: `GET /api/chat/threads`, `GET /api/chat/threads/{id}`, `GET /api/blackboard/tasks/{id}`.

- [ ] **Step 1: Write failing read-interface tests**

```python
def test_chat_thread_list_and_detail_are_owner_scoped() -> None:
    clear_store()
    mine = authenticated_client(USER.id)
    mine_thread = mine.post("/api/chat/threads", json={"title": "mine"}).json()["thread"]
    other_thread = authenticated_client(TEAM_LEAD.id).post(
        "/api/chat/threads", json={"title": "other"}
    ).json()["thread"]

    listed = mine.get("/api/chat/threads")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["items"]] == [mine_thread["id"]]
    assert mine.get(f"/api/chat/threads/{mine_thread['id']}").status_code == 200
    assert mine.get(f"/api/chat/threads/{other_thread['id']}").status_code == 404


def test_visible_task_detail_returns_card_and_timeline() -> None:
    clear_store()
    client = authenticated_client(USER.id)
    task_id = client.post(
        "/api/chat/messages", json={"content": "$research.request 查一下首屏经验"}
    ).json()["task"]["id"]
    response = client.get(f"/api/blackboard/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json()["task_card"]["task"]["id"] == task_id
    assert response.json()["posts"]
```

- [ ] **Step 2: Run tests and verify 404 from missing routes**

Run: `.venv/bin/python -m pytest tests/test_frontend_contracts.py -k "thread_list or visible_task" -v`

Expected: FAIL with route 404 responses.

- [ ] **Step 3: Add scoped store methods and route DTOs**

```python
# agentmesh/store.py
def list_chat_threads(self, user_id: str) -> list[ChatThread]:
    items = [thread for thread in self.chat_threads if thread.user_id == user_id]
    return sorted(items, key=lambda thread: thread.updated_at, reverse=True)
```

```python
# agentmesh/models.py
class ChatThreadDetail(BaseModel):
    thread: ChatThread
    messages: list[ChatMessage]


class BlackboardTaskDetail(BaseModel):
    task_card: BlackboardTaskCard
    posts: list[BlackboardPost]
```

```python
# agentmesh/routes/chat.py
@router.get("/threads", response_model=ItemsResponse)
def list_chat_threads(user: User = Depends(current_user)) -> ItemsResponse:
    return ItemsResponse(items=store.list_chat_threads(user.id))


@router.get("/threads/{thread_id}", response_model=ChatThreadDetail)
def chat_thread_detail(thread_id: str, user: User = Depends(current_user)) -> ChatThreadDetail:
    thread = store.get_chat_thread(thread_id)
    if thread is None or thread.user_id != user.id:
        raise HTTPException(status_code=404, detail="Chat thread not found")
    return ChatThreadDetail(thread=thread, messages=store.list_thread_messages(thread.id))
```

Add `GET /api/blackboard/tasks/{task_id}` beside task-card aggregation. Build one card using the same helper as the list endpoint and return only posts accepted by `post_visible_to_user`.

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_frontend_contracts.py tests/test_multiturn.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agentmesh/models.py agentmesh/store.py agentmesh/routes/chat.py agentmesh/routes/blackboard.py tests/test_frontend_contracts.py
git commit -m "Add scoped thread and task reads"
```

### Task 3: Establish the Typed React Data Layer and Auth Gate

**Files:**
- Modify: `agentmesh-demo/package.json`
- Modify: `agentmesh-demo/package-lock.json`
- Modify: `agentmesh-demo/vite.config.ts`
- Create: `agentmesh-demo/scripts/export_openapi.py`
- Create: `agentmesh-demo/src/api/generated/schema.ts`
- Create: `agentmesh-demo/src/api/client.ts`
- Create: `agentmesh-demo/src/app/queryClient.ts`
- Create: `agentmesh-demo/src/features/auth/api.ts`
- Create: `agentmesh-demo/src/features/auth/AuthProvider.tsx`
- Create: `agentmesh-demo/src/features/auth/LoginPage.tsx`
- Modify: `agentmesh-demo/src/main.tsx`
- Create: `agentmesh-demo/playwright.config.ts`
- Create: `agentmesh-demo/e2e/auth.spec.ts`
- Create: `agentmesh-demo/e2e/support/auth.ts`

**Interfaces:**
- Consumes: `/api/auth/login`, `/api/auth/me`, `/api/auth/logout`, `/api/bootstrap`.
- Produces: `apiRequest<T>()`, `ApiError`, `useAuth()`, shared `QueryClient`.

- [ ] **Step 1: Install dependencies and add failing auth browser test**

Run:

```bash
cd agentmesh-demo
npm install @tanstack/react-query
npm install --save-dev openapi-typescript @playwright/test
```

```ts
// agentmesh-demo/e2e/support/auth.ts
import type { Page } from '@playwright/test'

export async function loginAs(page: Page, userId: string, password: string) {
  await page.context().clearCookies()
  await page.goto('/digital-self')
  await page.getByLabel('账号').fill(userId)
  await page.getByLabel('密码').fill(password)
  await page.getByRole('button', { name: '登录' }).click()
}

export async function login(page: Page) {
  await loginAs(
    page,
    process.env.AGENTMESH_E2E_USER_ID ?? 'usr_current_designer',
    process.env.AGENTMESH_E2E_PASSWORD ?? 'designer123',
  )
}
```

```ts
// agentmesh-demo/e2e/auth.spec.ts
import { expect, test } from '@playwright/test'

import { login } from './support/auth'

test('login survives reload and logout clears the session', async ({ page }) => {
  await login(page)
  await expect(page.getByText('我的数字人', { exact: true })).toBeVisible()
  await page.reload()
  await expect(page.getByText('我的数字人', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: '退出登录' }).click()
  await expect(page.getByRole('button', { name: '登录' })).toBeVisible()
})
```

- [ ] **Step 2: Run test and verify the mock shell has no login gate**

Run: `cd agentmesh-demo && npx playwright test e2e/auth.spec.ts`

Expected: FAIL because no login form or auth provider exists.

- [ ] **Step 3: Add OpenAPI generation, HTTP seam, QueryClient, and AuthProvider**

```python
# agentmesh-demo/scripts/export_openapi.py
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from agentmesh.app import app  # noqa: E402

output = Path(__file__).resolve().parents[1] / "openapi.json"
output.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2), encoding="utf-8")
```

Add scripts:

```json
{
  "api:types": "../.venv/bin/python scripts/export_openapi.py && openapi-typescript openapi.json -o src/api/generated/schema.ts",
  "test:e2e": "playwright test"
}
```

```ts
// agentmesh-demo/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5178,
    proxy: { '/api': 'http://127.0.0.1:8010' },
  },
})
```

```ts
// agentmesh-demo/src/api/client.ts
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: unknown,
  ) {
    super(typeof detail === 'string' ? detail : `HTTP ${status}`)
  }
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...init,
    credentials: 'same-origin',
    headers: init.body instanceof FormData
      ? init.headers
      : { 'Content-Type': 'application/json', ...init.headers },
  })
  const payload = await response.json().catch(() => null)
  if (!response.ok) throw new ApiError(response.status, payload?.detail ?? payload)
  return payload as T
}
```

```ts
// agentmesh-demo/src/app/queryClient.ts
import { QueryClient } from '@tanstack/react-query'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 15_000, retry: false, refetchOnWindowFocus: false },
    mutations: { retry: false },
  },
})
```

```ts
// agentmesh-demo/src/features/auth/AuthProvider.tsx
export interface AuthContextValue {
  user: components['schemas']['User'] | null
  bootstrap: components['schemas']['BootstrapState'] | null
  loading: boolean
  login: (userId: string, password: string) => Promise<void>
  logout: () => Promise<void>
}
```

`AuthProvider` calls `/api/auth/me` and `/api/bootstrap`, treats 401 as signed out, clears `queryClient` on logout, and never stores a token.

Caches outside `AuthProvider` consume `useAuth()` and include `user.id`, `workspace.id`, and `project.id` in query keys where the resource is context-sensitive.

- [ ] **Step 4: Configure Playwright and verify auth**

```ts
// agentmesh-demo/playwright.config.ts
import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  use: { baseURL: 'http://127.0.0.1:5178', trace: 'retain-on-failure' },
  webServer: [
    {
      command: '.venv/bin/uvicorn agentmesh.app:app --port 8010',
      cwd: '..',
      port: 8010,
      reuseExistingServer: true,
      env: { AGENTMESH_DB_PATH: '/tmp/agentmesh-playwright.sqlite3' },
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 5178',
      port: 5178,
      reuseExistingServer: true,
    },
  ],
})
```

Run: `cd agentmesh-demo && npm run api:types && npm run build && npm run test:e2e -- e2e/auth.spec.ts`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agentmesh-demo/package.json agentmesh-demo/package-lock.json agentmesh-demo/vite.config.ts agentmesh-demo/scripts agentmesh-demo/src/api agentmesh-demo/src/app agentmesh-demo/src/features/auth agentmesh-demo/src/main.tsx agentmesh-demo/playwright.config.ts agentmesh-demo/e2e/auth.spec.ts
git commit -m "Add typed React auth foundation"
```

### Task 4: Serve the React Shell and Fix Responsive Accessibility

**Files:**
- Modify: `agentmesh/app.py:45-103`
- Modify: `agentmesh-demo/src/App.tsx`
- Modify: `agentmesh-demo/src/components/layout/AppLayout.tsx`
- Modify: `agentmesh-demo/src/components/layout/Sidebar.tsx`
- Modify: `agentmesh-demo/src/components/ui/Drawer.tsx`
- Modify: `agentmesh-demo/src/components/ui/Modal.tsx`
- Modify: `agentmesh-demo/src/components/ui/Tabs.tsx`
- Modify: `agentmesh-demo/src/components/ui/ToastViewport.tsx`
- Modify: `agentmesh-demo/src/index.css`
- Create: `agentmesh-demo/e2e/shell.spec.ts`
- Test: `tests/test_frontend_contracts.py`

**Interfaces:**
- Consumes: built `agentmesh-demo/dist` files and `useAuth()`.
- Produces: accessible app shell, mobile navigation, SPA routes, legacy fallback.

- [ ] **Step 1: Add failing shell tests**

```python
def test_react_route_uses_configured_index_without_swallowing_api_404(monkeypatch, tmp_path) -> None:
    import agentmesh.app as app_module

    index = tmp_path / "index.html"
    index.write_text('<div id="root"></div>', encoding="utf-8")
    monkeypatch.setattr(app_module, "FRONTEND_INDEX", index)
    client = TestClient(app)
    route = client.get("/digital-self")
    assert route.status_code == 200
    assert '<div id="root"></div>' in route.text
    api_missing = client.get("/api/does-not-exist")
    assert api_missing.status_code == 404
    assert api_missing.headers["content-type"].startswith("application/json")
```

```ts
// agentmesh-demo/e2e/shell.spec.ts
import { expect, test } from '@playwright/test'

for (const viewport of [
  { width: 390, height: 844 },
  { width: 768, height: 1024 },
  { width: 1512, height: 944 },
]) {
  test(`shell remains operable at ${viewport.width}px`, async ({ page }) => {
    await page.setViewportSize(viewport)
    await page.goto('/digital-self')

    await expect(page.locator('body')).toHaveJSProperty('scrollWidth', viewport.width)
    if (viewport.width === 390) {
      await expect(page.getByRole('button', { name: '打开导航' })).toBeVisible()
    }
  })
}
```

- [ ] **Step 2: Run tests and observe the missing React route and narrow mobile Workspace**

Run: `.venv/bin/python -m pytest tests/test_frontend_contracts.py -k configured_index -v`

Run: `cd agentmesh-demo && npm run test:e2e -- e2e/shell.spec.ts`

Expected: FAIL.

- [ ] **Step 3: Add static hosting and responsive shell**

In `agentmesh/app.py`, mount `/assets` from `agentmesh-demo/dist/assets`. Keep `/app.html` serving the old file. Add explicit React fallbacks for `/digital-self`, `/workspace`, `/insights`, `/knowledge`, `/collaboration`, and `/admin` descendants. Do not add an unrestricted catch-all that can turn API 404 responses into HTML.

Define the production paths once and return 503 when the frontend has not been built:

```python
FRONTEND_DIST = ROOT_DIR / "agentmesh-demo" / "dist"
FRONTEND_INDEX = FRONTEND_DIST / "index.html"


def react_index() -> FileResponse:
    if not FRONTEND_INDEX.exists():
        raise HTTPException(status_code=503, detail="React frontend is not built")
    return FileResponse(FRONTEND_INDEX)
```

Update `Sidebar` to render as a desktop aside at `lg` and as a controlled Drawer below `lg`. Add a top-bar navigation button. Change non-Workspace gutters to `px-4 py-4 md:px-8 md:py-8`. Make Workspace detail full-screen below `md`.

Use these accessibility contracts:

```tsx
<div role="tablist" aria-label={label} className="flex overflow-x-auto">
  {items.map((item) => (
    <button
      key={item.key}
      role="tab"
      aria-selected={item.key === value}
      tabIndex={item.key === value ? 0 : -1}
      onClick={() => onChange(item.key)}
    >
      {item.label}
    </button>
  ))}
</div>
```

Drawer and Modal receive `titleId`, focus the close button when opened, trap Tab within the overlay, restore the triggering element on close, and support Escape. ToastViewport gets `role="status" aria-live="polite"`.

- [ ] **Step 4: Verify shell and routes**

Run: `.venv/bin/python -m pytest tests/test_frontend_contracts.py -k react_route -v`

Run: `cd agentmesh-demo && npm run build && npm run test:e2e -- e2e/shell.spec.ts`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agentmesh/app.py agentmesh-demo/src/App.tsx agentmesh-demo/src/components agentmesh-demo/src/index.css agentmesh-demo/e2e/shell.spec.ts tests/test_frontend_contracts.py
git commit -m "Serve responsive React shell"
```

### Task 5: Connect Digital Self and Read-Only Insights

**Files:**
- Create: `agentmesh-demo/src/features/digital-self/api.ts`
- Create: `agentmesh-demo/src/features/digital-self/queries.ts`
- Create: `agentmesh-demo/src/features/insights/api.ts`
- Create: `agentmesh-demo/src/features/insights/queries.ts`
- Modify: `agentmesh-demo/src/pages/DigitalSelf.tsx`
- Modify: `agentmesh-demo/src/components/digital-self/WelcomeHero.tsx`
- Modify: `agentmesh-demo/src/components/digital-self/IdentityCard.tsx`
- Modify: `agentmesh-demo/src/components/digital-self/UnderstandingList.tsx`
- Modify: `agentmesh-demo/src/components/digital-self/TodayWork.tsx`
- Modify: `agentmesh-demo/src/components/digital-self/RecentGrowth.tsx`
- Modify: `agentmesh-demo/src/components/digital-self/MyImpact.tsx`
- Modify: `agentmesh-demo/src/pages/Insights.tsx`
- Create: `agentmesh-demo/e2e/digital-self-insights.spec.ts`

**Interfaces:**
- Consumes: `/api/bootstrap`, `/api/activity/today`, `/api/memory/overview`, `/api/market/participation`, `/api/blackboard/task-cards`, `/api/audit`.
- Produces: server-derived Digital Self summary and factual read-only Insights projection.

- [ ] **Step 1: Write the failing server-data browser flow**

```ts
import { expect, test } from '@playwright/test'

import { login } from './support/auth'

test('digital self and insights render server records instead of mock copy', async ({ page }) => {
  await login(page)
  const created = await page.request.post('/api/chat/messages', {
    data: { content: `$research.request 洞察投影验证 ${Date.now()}` },
  })
  expect(created.ok()).toBeTruthy()
  const task = (await created.json()).task

  await page.goto('/digital-self')
  await expect(page.getByTestId('digital-self-summary')).toHaveAttribute('data-source', 'server')
  await expect(page.getByText('林知夏', { exact: false }).first()).toBeVisible()

  await page.goto('/insights')
  await expect(page.getByTestId(`insight-task-${task.id}`)).toBeVisible()
  await expect(page.getByText('工作洞察', { exact: true })).toBeVisible()
})
```

- [ ] **Step 2: Run and verify both pages still use mock data**

Run: `cd agentmesh-demo && npm run test:e2e -- e2e/digital-self-insights.spec.ts`

Expected: FAIL because both pages import `mockData.ts` and do not expose server-backed resources.

- [ ] **Step 3: Add factual projections without inventing new domain state**

```ts
// agentmesh-demo/src/features/digital-self/api.ts
import type { components } from '../../api/generated/schema'
import { apiRequest } from '../../api/client'

type BootstrapState = components['schemas']['BootstrapState']
type ActivityTodayResponse = components['schemas']['ActivityTodayResponse']
type MemoryOverviewResponse = components['schemas']['MemoryOverviewResponse']
type MarketParticipation = components['schemas']['MarketParticipation']
type BlackboardTaskCardsResponse = components['schemas']['BlackboardTaskCardsResponse']
type AuditListResponse = components['schemas']['AuditListResponse']

export async function loadDigitalSelfSummary() {
  const [bootstrap, activity, memory, participation] = await Promise.all([
    apiRequest<BootstrapState>('/api/bootstrap'),
    apiRequest<ActivityTodayResponse>('/api/activity/today'),
    apiRequest<MemoryOverviewResponse>('/api/memory/overview'),
    apiRequest<MarketParticipation>('/api/market/participation'),
  ])
  return { bootstrap, activity, memory, participation }
}

export async function loadInsightsProjection(period: 'today' | 'week' | 'month') {
  const [bootstrap, activity, memory, tasks, audit] = await Promise.all([
    apiRequest<BootstrapState>('/api/bootstrap'),
    apiRequest<ActivityTodayResponse>('/api/activity/today'),
    apiRequest<MemoryOverviewResponse>('/api/memory/overview'),
    apiRequest<BlackboardTaskCardsResponse>('/api/blackboard/task-cards'),
    apiRequest<AuditListResponse>(`/api/audit?limit=${period === 'today' ? 25 : 80}`),
  ])
  return { period, bootstrap, activity, memory, tasks: tasks.items, audit }
}
```

Digital Self 显示当前用户、Personal Agent、Workspace、Project、记忆计数、当前活动和市场参与状态。`UnderstandingList` 在第一阶段显示“尚无可确认的数字人理解”空态，不提供假操作。`MyImpact` 在第二阶段接口上线前，只显示真实活动和记忆摘要。

Insights 显示当前项目、可见任务卡、活动、记忆计数和最近审计事件。第一阶段不生成判断文案、复盘候选、重复问题或不可执行的按钮；没有后端记录的区域显示明确空态。

- [ ] **Step 4: Verify both pages and the build**

Run: `cd agentmesh-demo && npm run build && npm run test:e2e -- e2e/digital-self-insights.spec.ts`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agentmesh-demo/src/features/digital-self agentmesh-demo/src/features/insights agentmesh-demo/src/pages/DigitalSelf.tsx agentmesh-demo/src/pages/Insights.tsx agentmesh-demo/src/components/digital-self agentmesh-demo/e2e/digital-self-insights.spec.ts
git commit -m "Connect digital self and insights"
```

### Task 6: Migrate Workspace, Sources, Briefs, Search, and Uploads

**Files:**
- Create: `agentmesh-demo/src/features/workspace/api.ts`
- Create: `agentmesh-demo/src/features/workspace/queries.ts`
- Create: `agentmesh-demo/src/features/workspace/types.ts`
- Modify: `agentmesh-demo/src/pages/Workspace.tsx`
- Modify: `agentmesh-demo/src/components/workspace/ConversationNav.tsx`
- Modify: `agentmesh-demo/src/components/workspace/ConversationThread.tsx`
- Modify: `agentmesh-demo/src/components/workspace/Composer.tsx`
- Modify: `agentmesh-demo/src/components/workspace/DetailPanel.tsx`
- Create: `agentmesh-demo/e2e/workspace.spec.ts`

**Interfaces:**
- Consumes: Task 2 thread APIs, `/api/chat/skills`, `/api/chat/messages`, `/api/documents`, `/api/search`.
- Produces: `useThreads()`, `useThread(id)`, `useSendMessage(id)`, `useUploadDocument()`, resource-driven detail panel.

- [ ] **Step 1: Write failing Workspace browser flow**

```ts
import { expect, test } from '@playwright/test'

import { login } from './support/auth'

test('private chat and explicit skill persist with different traces', async ({ page }) => {
  await login(page)
  await page.goto('/workspace')
  await page.getByRole('button', { name: '开始新对话' }).click()
  await page.getByLabel('消息').fill(`只记录私聊 ${Date.now()}`)
  await page.getByRole('button', { name: '发送' }).click()
  await expect(page.getByText('默认私有')).toBeVisible()
  await page.getByLabel('消息').fill('$system.info 当前系统状态')
  await page.getByRole('button', { name: '发送' }).click()
  await expect(page.getByText('入口：skill')).toBeVisible()
  await page.reload()
  await expect(page.getByText('当前系统状态')).toBeVisible()
})
```

- [ ] **Step 2: Run and verify mock Workspace failure**

Run: `cd agentmesh-demo && npm run test:e2e -- e2e/workspace.spec.ts`

Expected: FAIL because the current Composer uses a timer and no message is persisted.

- [ ] **Step 3: Add typed APIs and query invalidation**

```ts
// agentmesh-demo/src/features/workspace/api.ts
import { apiRequest } from '../../api/client'
import type { components } from '../../api/generated/schema'

type ChatThread = components['schemas']['ChatThread']
type ChatThreadDetail = components['schemas']['ChatThreadDetail']
type ChatResponse = components['schemas']['ChatResponse']

export const workspaceApi = {
  listThreads: () => apiRequest<{ items: ChatThread[] }>('/api/chat/threads'),
  getThread: (id: string, signal?: AbortSignal) =>
    apiRequest<ChatThreadDetail>(`/api/chat/threads/${encodeURIComponent(id)}`, { signal }),
  createThread: (title: string) =>
    apiRequest<{ thread: ChatThread }>('/api/chat/threads', { method: 'POST', body: JSON.stringify({ title }) }),
  sendMessage: (content: string, threadId: string) =>
    apiRequest<ChatResponse>('/api/chat/messages', {
      method: 'POST',
      body: JSON.stringify({ content, thread_id: threadId }),
    }),
}
```

消息发送成功后，用服务端返回的 `user_message` 和 `assistant_message` 替换 pending 消息，再使 thread detail、thread list、bootstrap、task cards、Inbox、memory overview 和 Blackboard 缓存失效。失败时保留 `failed` 草稿和重试动作，不得声称消息已经持久化。

Composer 使用真实的 `<textarea aria-label="消息">`。Enter 发送，Shift+Enter 换行；mutation pending 时禁止重复提交，并删除所有 timer 假生成逻辑。

- [ ] **Step 4: Verify Workspace and backend regression**

Run: `cd agentmesh-demo && npm run build && npm run test:e2e -- e2e/workspace.spec.ts`

Run: `.venv/bin/python -m pytest tests/test_chat_flow.py tests/test_multiturn.py tests/test_documents.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agentmesh-demo/src/features/workspace agentmesh-demo/src/pages/Workspace.tsx agentmesh-demo/src/components/workspace agentmesh-demo/e2e/workspace.spec.ts
git commit -m "Connect React workspace to AgentMesh"
```

### Task 7: Migrate Inbox, Memory, and Governance

**Files:**
- Create: `agentmesh-demo/src/features/knowledge/api.ts`
- Create: `agentmesh-demo/src/features/knowledge/queries.ts`
- Modify: `agentmesh-demo/src/pages/Knowledge.tsx`
- Modify: `agentmesh-demo/src/components/knowledge/PendingKnowledgeCard.tsx`
- Modify: `agentmesh-demo/src/components/knowledge/ConfirmKnowledgeModal.tsx`
- Create: `agentmesh-demo/src/features/knowledge/InboxPanel.tsx`
- Create: `agentmesh-demo/e2e/knowledge-governance.spec.ts`

**Interfaces:**
- Consumes: `/api/inbox`, dedicated Inbox commands, `/api/memory/overview`, memory rollups, document detail/update.
- Produces: server-driven Knowledge tabs and Brief to team-candidate flow.

- [ ] **Step 1: Write failing governance flow**

```ts
import { expect, test } from '@playwright/test'

import { login } from './support/auth'

test('brief confirmation creates a team candidate without local promotion', async ({ page }) => {
  await login(page)
  await page.goto('/workspace')
  await page.getByLabel('消息').fill('$brief.create 生成端到端验证 Brief')
  await page.getByRole('button', { name: '发送' }).click()
  await page.goto('/knowledge')
  await page.getByRole('tab', { name: /待我确认/ }).click()
  await page.getByRole('button', { name: '查看并确认 Brief' }).click()
  await page.getByLabel('Brief 正文').fill('端到端验证后的 Brief 正文')
  await page.getByRole('button', { name: '确认并沉淀' }).click()
  await expect(page.getByText('团队候选')).toBeVisible()
})
```

- [ ] **Step 2: Run and verify static candidate failure**

Run: `cd agentmesh-demo && npm run test:e2e -- e2e/knowledge-governance.spec.ts`

Expected: FAIL because the current Knowledge page always renders `NEW_KNOWLEDGE` and local counters.

- [ ] **Step 3: Replace mock knowledge state with API resources**

```ts
export const knowledgeKeys = {
  overview: (projectId: string, filters: Record<string, string>) =>
    ['knowledge', 'overview', projectId, filters] as const,
  inbox: (includeSnoozed: boolean) => ['inbox', includeSnoozed] as const,
  document: (id: string) => ['documents', id] as const,
}
```

`ConfirmKnowledgeModal` receives `{ candidateId, item, allowedActions }`. It no longer owns a three-step business state machine. It submits the server command, waits for the canonical result, then invalidates Inbox, memory overview, bootstrap metrics, and document detail.

Map errors exactly: 400 shows missing source memory, 403 hides no data and reports permission, 409 refreshes the item and reports that another action already completed it.

- [ ] **Step 4: Verify governance flow and role behavior**

Run: `cd agentmesh-demo && npm run build && npm run test:e2e -- e2e/knowledge-governance.spec.ts`

Run: `.venv/bin/python -m pytest tests/test_permissions.py tests/test_chat_flow.py -k "memory or inbox or brief" -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agentmesh-demo/src/features/knowledge agentmesh-demo/src/pages/Knowledge.tsx agentmesh-demo/src/components/knowledge agentmesh-demo/e2e/knowledge-governance.spec.ts
git commit -m "Connect knowledge governance flow"
```

### Task 8: Migrate Collaboration, Blackboard, Tasks, and Market

**Files:**
- Create: `agentmesh-demo/src/features/collaboration/api.ts`
- Create: `agentmesh-demo/src/features/collaboration/queries.ts`
- Modify: `agentmesh-demo/src/pages/Collaboration.tsx`
- Modify: `agentmesh-demo/src/components/collaboration/HelpRequestCard.tsx`
- Modify: `agentmesh-demo/src/components/collaboration/MyCollabCard.tsx`
- Modify: `agentmesh-demo/src/components/collaboration/CollabTimelineDrawer.tsx`
- Create: `agentmesh-demo/e2e/collaboration.spec.ts`

**Interfaces:**
- Consumes: task cards/detail, Blackboard pagination and commands, market board/status/participation.
- Produces: task-ID-driven collaboration views and controlled market refresh.

- [ ] **Step 1: Write failing market and task browser flow**

```ts
import { expect, test } from '@playwright/test'

import { login } from './support/auth'

test('collaboration shows server market state and task detail', async ({ page }) => {
  await login(page)
  const created = await page.request.post('/api/chat/messages', {
    data: { content: `$research.request 协作详情验证 ${Date.now()}` },
  })
  expect(created.ok()).toBeTruthy()
  await page.goto('/collaboration')
  await expect(page.getByText(/市场已关闭|市场运行中/)).toBeVisible()
  await page.getByRole('tab', { name: /我发起的/ }).click()
  const first = page.getByRole('button', { name: '查看协作详情' }).first()
  await expect(first).toBeVisible()
  await first.click()
  await expect(page.getByRole('dialog')).toContainText('任务阶段')
})
```

- [ ] **Step 2: Run and verify fixed mock failure**

Run: `cd agentmesh-demo && npm run test:e2e -- e2e/collaboration.spec.ts`

Expected: FAIL because counts, requests, timeline, and authorization are local mock data.

- [ ] **Step 3: Add collaboration APIs and server-driven tabs**

```ts
export const collaborationKeys = {
  cards: ['collaboration', 'task-cards'] as const,
  task: (id: string) => ['collaboration', 'task', id] as const,
  board: (page: number, taskId?: string) => ['collaboration', 'board', page, taskId] as const,
  market: ['collaboration', 'market'] as const,
  participation: ['collaboration', 'participation'] as const,
}
```

Derive tab counts from returned task cards and server status, not from fixed numbers. `CollabTimelineDrawer` receives `taskId`, loads `/api/blackboard/tasks/{taskId}`, and renders the returned card and posts. Lock, unlock, handoff, dispatch, reply, read, and memory-candidate buttons come from `allowed_actions`.

Poll market and worker state only while the collaboration market tab is visible. Use a 30-second interval, stop polling when `document.hidden` is true, and display `enabled`, `running`, and `last_error` separately.

- [ ] **Step 4: Verify collaboration and authorization**

Run: `cd agentmesh-demo && npm run build && npm run test:e2e -- e2e/collaboration.spec.ts`

Run: `.venv/bin/python -m pytest tests/test_market_status.py tests/test_market_participation.py tests/test_marketplace_scout.py tests/test_chat_flow.py -k "blackboard or task or market" -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agentmesh-demo/src/features/collaboration agentmesh-demo/src/pages/Collaboration.tsx agentmesh-demo/src/components/collaboration agentmesh-demo/e2e/collaboration.spec.ts
git commit -m "Connect collaboration and market views"
```

### Task 9: Migrate the Admin and Operations Center

**Files:**
- Create: `agentmesh-demo/src/features/admin/api.ts`
- Create: `agentmesh-demo/src/features/admin/AdminLayout.tsx`
- Create: `agentmesh-demo/src/features/admin/AgentsPage.tsx`
- Create: `agentmesh-demo/src/features/admin/MembersPage.tsx`
- Create: `agentmesh-demo/src/features/admin/PoliciesPage.tsx`
- Create: `agentmesh-demo/src/features/admin/IntegrationsPage.tsx`
- Create: `agentmesh-demo/src/features/admin/AuditPage.tsx`
- Modify: `agentmesh-demo/src/components/layout/SettingsDrawer.tsx`
- Modify: `agentmesh-demo/src/App.tsx`
- Create: `agentmesh-demo/e2e/admin.spec.ts`

**Interfaces:**
- Consumes: users, teams, workspaces, projects, permission policies, risk policies, Agents, models, tools, scheduled definitions, O2, data sources, health, audit, worker status.
- Produces: capability-gated `/admin/*` routes with separate personal/public Agent state.

- [ ] **Step 1: Write failing role-gated admin test**

```ts
import { expect, test } from '@playwright/test'

import { loginAs } from './support/auth'

test('regular user cannot enter admin routes and admin can manage users', async ({ page }) => {
  await loginAs(page, 'usr_current_designer', 'designer123')
  await page.goto('/admin/members')
  await expect(page.getByText('没有访问权限')).toBeVisible()

  await loginAs(page, 'usr_admin', 'admin123')
  await page.goto('/admin/members')
  await expect(page.getByRole('heading', { name: '成员管理' })).toBeVisible()
  await expect(page.getByRole('button', { name: '新建成员' })).toBeVisible()
})
```

- [ ] **Step 2: Run and verify admin routes are absent**

Run: `cd agentmesh-demo && npm run test:e2e -- e2e/admin.spec.ts`

Expected: FAIL with redirect or missing route.

- [ ] **Step 3: Add capability-gated admin routes and isolated forms**

```tsx
export function RequireCapability({ capability, children }: { capability: string; children: React.ReactNode }) {
  const { bootstrap } = useAuth()
  if (!bootstrap?.capabilities.includes(capability)) {
    return <div role="alert">没有访问权限</div>
  }
  return <>{children}</>
}
```

Use separate query keys and forms for Personal Agent and Public Agent. Always load the selected Agent's grants before rendering checkboxes. Validate all model and tool selections before submitting sequential endpoints; after any partial failure, refetch Agent, model, and tool state before reporting the exact failed step.

The Settings drawer entries become `NavLink` elements and only render when their required capability is present. Theme and preference toggles remain hidden because Stage 1 has no persistence contract.

- [ ] **Step 4: Verify admin surface and backend roles**

Run: `cd agentmesh-demo && npm run build && npm run test:e2e -- e2e/admin.spec.ts`

Run: `.venv/bin/python -m pytest tests/test_permissions.py tests/test_o2.py tests/test_health.py tests/test_risk.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agentmesh-demo/src/features/admin agentmesh-demo/src/components/layout/SettingsDrawer.tsx agentmesh-demo/src/App.tsx agentmesh-demo/e2e/admin.spec.ts
git commit -m "Add React admin operations center"
```

### Task 10: Cut Over the Root Route and Remove Legacy State

**Files:**
- Modify: `agentmesh/app.py:91-103`
- Remove: `app.html`
- Remove: `agentmesh-demo/src/data/mockData.ts`
- Remove: `agentmesh-demo/src/store/DemoContext.tsx`
- Modify: every remaining importer under `agentmesh-demo/src/`
- Modify: `README.md:47-96`
- Modify: `tests/test_chat_flow.py:92-98`
- Create: `agentmesh-demo/e2e/parity.spec.ts`

**Interfaces:**
- Consumes: all Stage 1 migrated slices.
- Produces: React at `/`, no production mock state, no legacy UI route.

- [ ] **Step 1: Write failing cutover and parity checks**

```python
def test_root_uses_react_index_and_legacy_route_is_removed(monkeypatch, tmp_path) -> None:
    import agentmesh.app as app_module

    index = tmp_path / "index.html"
    index.write_text('<div id="root"></div>', encoding="utf-8")
    monkeypatch.setattr(app_module, "FRONTEND_INDEX", index)
    client = TestClient(app)
    root = client.get("/")
    assert root.status_code == 200
    assert '<div id="root"></div>' in root.text
    assert client.get("/app.html").status_code == 404
```

```ts
import { expect, test } from '@playwright/test'

import { login } from './support/auth'

const routes = [
  { path: '/digital-self', heading: '我的数字人' },
  { path: '/workspace', heading: 'AI 工作台' },
  { path: '/insights', heading: '工作洞察' },
  { path: '/knowledge', heading: '我的知识' },
  { path: '/collaboration', heading: '协作网络' },
]

for (const route of routes) {
  test(`${route.path} renders its real route shell`, async ({ page }) => {
    await login(page)
    await page.goto(route.path)
    await expect(page.getByText(route.heading, { exact: true }).first()).toBeVisible()
  })
}
```

- [ ] **Step 2: Run and verify legacy route and mock imports still exist**

Run: `.venv/bin/python -m pytest tests/test_chat_flow.py -k "root_uses_react" -v`

Run: `cd agentmesh-demo && npm run test:e2e -- e2e/parity.spec.ts`

Expected: FAIL before cutover.

- [ ] **Step 3: Switch root, remove legacy files, and update docs**

Change `/` to return the Vite index. Remove the old `/app.html` route rather than keeping an alias. Delete `mockData.ts`, `DemoContext.tsx`, and every production import that depends on them.

Update README local run instructions to build the frontend before starting FastAPI for production-mode verification and to use Vite during development. Do not include seed passwords in production UI copy.

- [ ] **Step 4: Run full release gate**

Run:

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check .
cd agentmesh-demo
npm run api:types
npm run build
npm run test:e2e
```

Expected: 279 existing backend tests plus new contract tests PASS, Ruff PASS, TypeScript/Vite build PASS, all Playwright flows PASS.

Manually verify at 390px, 768px, and 1512px: navigation, Workspace Composer, details, Tabs, Modal focus, Drawer focus return, reduced-motion behavior, and no horizontal overflow.

- [ ] **Step 5: Commit**

```bash
git add agentmesh/app.py agentmesh-demo README.md tests/test_chat_flow.py
git commit -m "Replace legacy AgentMesh frontend"
```

## Stage 1 Completion Gate

- React is the only production frontend.
- Every valid old UI operation has a React entry.
- All permission and state transitions remain server-side.
- No mock business data, local business counters, fake timers, fallback skills, hard-coded login helpers, or handler-less controls remain in production code.
- Browser checks cover user, team lead, and admin roles.
- Rollback before Task 10 is route-only. After Task 10, rollback uses the previous deployment artifact and does not change SQLite data.
