# AgentMesh Product Capabilities Stage 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the React demo's delegated collaboration, project review, digital-understanding, impact, and preference concepts into persistent FastAPI capabilities.

**Architecture:** Add three focused backend seams after the React replacement is complete: persisted collaboration records around the existing PersonalAgent delegated-answer logic, persisted project reviews that emit real team-memory candidates, and a personal-profile surface for understanding, impact, and preferences. React consumes stable resource IDs and canonical server state; no business counter or state machine returns to the client.

**Tech Stack:** Python 3.12+, FastAPI, Pydantic, SQLiteStore, React 18, TypeScript 5.6, TanStack Query, generated OpenAPI types, Playwright.

## Global Constraints

- Stage 1 must be complete before starting this plan.
- Reuse `PersonalAgent.grant_consent`, `revoke_consent`, `answer_for_peer`, `resolve_delegated_answer`, and `adopt_delegated_answer`; do not rewrite answer synthesis.
- A delegated answer is an internal collaboration record, not a privacy guarantee.
- High-sensitivity matches always require target-user confirmation.
- Adoption is idempotent and awards at most one shadow point and one lineage edge.
- Project review is the only new path in this stage that creates a knowledge candidate.
- Understanding, impact, and preferences are current-user scoped.
- No contribution redemption, anti-collusion, semantic-leak prevention, external writes, or real-time transport.
- Every task adds backend contract tests and a real-browser flow where users can observe the behavior.

---

## File Map

- `agentmesh/models.py`: `DelegatedAnswerRecord`, `ProjectReview`, `AgentUnderstanding`, `UserPreference`, request and response DTOs.
- `agentmesh/store.py`: typed collection access and idempotent lookup helpers.
- `agentmesh/agents.py`: persist delegated-answer transitions while retaining synthesis behavior.
- `agentmesh/routes/collaboration.py`: consent, request, decision, answer, adoption, contribution endpoints.
- `agentmesh/routes/insights.py`: insight projection and project-review commands.
- `agentmesh/routes/profile.py`: understanding, impact, and preference endpoints.
- `agentmesh/app.py`: register the three new routers.
- `agentmesh-demo/src/features/collaboration/`: request and answer UI.
- `agentmesh-demo/src/features/insights/`: persisted review UI.
- `agentmesh-demo/src/features/digital-self/`: understanding and impact UI.
- `agentmesh-demo/src/features/settings/`: persisted preferences.

---

### Task 1: Persist Delegated Answer Records

**Files:**
- Modify: `agentmesh/models.py:474-556`
- Modify: `agentmesh/store.py:230-240,400-426`
- Modify: `agentmesh/agents.py:989-1115`
- Test: `tests/test_delegated_answer.py`

**Interfaces:**
- Consumes: existing `DelegatedAnswer`, `ConsentGrant`, `ContributionPoint`, `MemoryRelation`.
- Produces: `DelegatedAnswerRecord`, `store.save_delegated_answer()`, `store.get_delegated_answer()`.

- [ ] **Step 1: Write failing persistence and idempotency tests**

```python
from agentmesh.models import DelegatedAnswerRecord


def test_answer_for_peer_persists_a_record_for_both_answered_and_pending() -> None:
    agent = _reset()
    _rich_target_memory()
    pending = agent.answer_for_peer(ASKER, TARGET, QUESTION)
    assert pending.record_id is not None
    pending_record = store.get_delegated_answer(pending.record_id)
    assert pending_record is not None
    assert pending_record.status == "awaiting_confirm"
    assert pending_record.asker_id == ASKER.id
    assert pending_record.target_id == TARGET.id

    agent.grant_consent(TARGET, ASKER)
    answered = agent.answer_for_peer(ASKER, TARGET, "降级阈值怎么设")
    assert isinstance(store.get_delegated_answer(answered.record_id), DelegatedAnswerRecord)


def test_adopting_the_same_record_twice_returns_the_existing_result() -> None:
    agent = _reset()
    _rich_target_memory()
    agent.grant_consent(TARGET, ASKER)
    answer = agent.answer_for_peer(ASKER, TARGET, QUESTION)
    first = agent.adopt_delegated_answer_record(ASKER, answer.record_id)
    second = agent.adopt_delegated_answer_record(ASKER, answer.record_id)
    assert first == second
    assert len(store.list_contribution_points(awarded_to_id=TARGET.id)) == 1
```

- [ ] **Step 2: Run tests and verify missing model and methods**

Run: `.venv/bin/python -m pytest tests/test_delegated_answer.py -k "persists_a_record or same_record_twice" -v`

Expected: FAIL because `record_id`, `DelegatedAnswerRecord`, and store methods do not exist.

- [ ] **Step 3: Add the record model and persist every transition**

```python
# agentmesh/models.py
class DelegatedAnswerRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("delegated"))
    asker_id: str
    target_id: str
    workspace_id: str
    question: str
    status: DelegatedAnswerStatus
    answer: str | None = None
    citations: list[Source] = Field(default_factory=list)
    confidence: AnswerConfidence = AnswerConfidence.UNSET
    inbox_item_id: str | None = None
    adopted_memory_id: str | None = None
    contribution_point_id: str | None = None
    memory_relation_id: str | None = None
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class DelegatedAnswer(BaseModel):
    status: DelegatedAnswerStatus
    answer: str | None = None
    citations: list[Source] = Field(default_factory=list)
    confidence: AnswerConfidence = AnswerConfidence.UNSET
    inbox_item: InboxItem | None = None
    record_id: str | None = None
```

```python
# agentmesh/store.py
@property
def delegated_answers(self) -> list[DelegatedAnswerRecord]:
    return self._list("delegated_answers", DelegatedAnswerRecord)


def save_delegated_answer(self, record: DelegatedAnswerRecord) -> DelegatedAnswerRecord:
    self._upsert("delegated_answers", record)
    return record


def get_delegated_answer(self, record_id: str) -> DelegatedAnswerRecord | None:
    return self._get("delegated_answers", record_id, DelegatedAnswerRecord)


def list_delegated_answers_for_user(self, user_id: str) -> list[DelegatedAnswerRecord]:
    items = [item for item in self.delegated_answers if user_id in {item.asker_id, item.target_id}]
    return sorted(items, key=lambda item: item.updated_at, reverse=True)
```

Create the record before running the consent gate. Save its Inbox ID for pending answers, save answer/citations/confidence for completed answers, and update the same record on approve or deny. `adopt_delegated_answer_record` validates that the caller is `asker_id`, requires citations, returns existing IDs if already adopted, otherwise delegates to the existing adoption method and stores all three generated IDs.

- [ ] **Step 4: Run delegated and market tests**

Run: `.venv/bin/python -m pytest tests/test_delegated_answer.py tests/test_marketplace_scout.py -v`

Expected: PASS, including existing raw-body and high-sensitivity guards.

- [ ] **Step 5: Commit**

```bash
git add agentmesh/models.py agentmesh/store.py agentmesh/agents.py tests/test_delegated_answer.py
git commit -m "Persist delegated answer records"
```

### Task 2: Expose Consent, Decision, Answer, and Adoption APIs

**Files:**
- Create: `agentmesh/routes/collaboration.py`
- Modify: `agentmesh/models.py`
- Modify: `agentmesh/app.py:21-88`
- Modify: `agentmesh/routes/inbox.py:137-199`
- Test: `tests/test_collaboration_api.py`

**Interfaces:**
- Consumes: Task 1 record store, current user, existing PersonalAgent methods.
- Produces: `/api/collaboration/consents`, `/requests`, `/answers/{id}`, `/answers/{id}/adopt`.

- [ ] **Step 1: Write failing API authorization tests**

```python
from agentmesh.models import MemoryLayer, UserMemoryItem
from agentmesh.seed import PROJECT, TEAM_LEAD, USER, WORKSPACE
from agentmesh.store import store
from tests.test_chat_flow import authenticated_client, clear_store


def _add_target_memory_for_api() -> None:
    store.add_user_memory_item(
        UserMemoryItem(
            user_id=USER.id,
            layer=MemoryLayer.MID_TERM,
            title="降级预案",
            summary="核心链路保底，按 QPS 阶梯降级。",
            source_kind="project_review",
            memory_type="decision",
            workspace_id=WORKSPACE.id,
            project_id=PROJECT.id,
        )
    )


def test_consent_lifecycle_is_grantor_scoped() -> None:
    clear_store()
    grantor = authenticated_client(USER.id)
    created = grantor.put(f"/api/collaboration/consents/{TEAM_LEAD.id}")
    assert created.status_code == 200
    assert created.json()["item"]["grantor_id"] == USER.id
    listed = grantor.get("/api/collaboration/consents").json()["items"]
    assert [item["grantee_id"] for item in listed] == [TEAM_LEAD.id]
    assert grantor.delete(f"/api/collaboration/consents/{TEAM_LEAD.id}").status_code == 200


def test_only_target_decides_and_only_asker_adopts() -> None:
    clear_store()
    _add_target_memory_for_api()
    asker = authenticated_client(TEAM_LEAD.id)
    pending = asker.post(
        "/api/collaboration/requests",
        json={"target_id": USER.id, "question": "降级预案怎么做"},
    ).json()["item"]
    target = authenticated_client(USER.id)

    assert asker.post(
        f"/api/collaboration/answers/{pending['id']}/decision", json={"action": "approve"}
    ).status_code == 403
    decided = target.post(
        f"/api/collaboration/answers/{pending['id']}/decision", json={"action": "approve"}
    )
    assert decided.status_code == 200
    assert target.post(f"/api/collaboration/answers/{pending['id']}/adopt").status_code == 403
    assert asker.post(f"/api/collaboration/answers/{pending['id']}/adopt").status_code == 200
```

- [ ] **Step 2: Run tests and verify route 404**

Run: `.venv/bin/python -m pytest tests/test_collaboration_api.py -v`

Expected: FAIL because the collaboration router does not exist.

- [ ] **Step 3: Add explicit request models and route authorization**

```python
# agentmesh/models.py
class DelegatedAnswerCreateRequest(BaseModel):
    target_id: str = Field(min_length=1, max_length=120)
    question: str = Field(min_length=1, max_length=1000)


class DelegatedAnswerDecisionRequest(BaseModel):
    action: str = Field(pattern="^(approve|deny)$")
```

```python
# agentmesh/routes/collaboration.py
router = APIRouter(prefix="/api/collaboration", tags=["collaboration"])

@router.post("/requests", response_model=ItemResponse)
def create_delegated_request(
    request: DelegatedAnswerCreateRequest,
    user: User = Depends(current_user),
) -> ItemResponse:
    target = store.get_user(request.target_id)
    if target is None or target.workspace_id != user.workspace_id:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == user.id:
        raise HTTPException(status_code=400, detail="Cannot request a delegated answer from yourself")
    answer = agent.answer_for_peer(user, target, request.question)
    record = store.get_delegated_answer(answer.record_id or "")
    if record is None:
        raise HTTPException(status_code=500, detail="Delegated answer record was not persisted")
    return ItemResponse(item=record)


@router.get("/consents", response_model=ItemsResponse)
def list_consents(user: User = Depends(current_user)) -> ItemsResponse:
    items = [grant for grant in store.consent_grants if grant.grantor_id == user.id and grant.active]
    return ItemsResponse(items=items)


@router.put("/consents/{grantee_id}", response_model=ItemResponse)
def grant_consent(grantee_id: str, user: User = Depends(current_user)) -> ItemResponse:
    grantee = store.get_user(grantee_id)
    if grantee is None or grantee.workspace_id != user.workspace_id:
        raise HTTPException(status_code=404, detail="User not found")
    return ItemResponse(item=agent.grant_consent(user, grantee))


@router.delete("/consents/{grantee_id}", response_model=StatusResponse)
def revoke_consent(grantee_id: str, user: User = Depends(current_user)) -> StatusResponse:
    grantee = store.get_user(grantee_id)
    if grantee is None or grantee.workspace_id != user.workspace_id:
        raise HTTPException(status_code=404, detail="User not found")
    agent.revoke_consent(user, grantee)
    return StatusResponse(status="ok")
```

Add list endpoint filters `inbound|outbound|answered|awaiting_confirm|denied`. Decision checks `target_id == user.id` and calls `resolve_delegated_answer_record`. Detail only returns records where the current user is asker or target. Adoption checks `asker_id == user.id` and returns the adopted memory, contribution point, and relation IDs.

Return citation titles and references, never target `UserMemoryItem` bodies.

- [ ] **Step 4: Run API and security tests**

Run: `.venv/bin/python -m pytest tests/test_collaboration_api.py tests/test_delegated_answer.py tests/test_permissions.py -v`

Expected: PASS.

Run: `.venv/bin/ruff check agentmesh tests/test_collaboration_api.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agentmesh/models.py agentmesh/routes/collaboration.py agentmesh/routes/inbox.py agentmesh/app.py tests/test_collaboration_api.py
git commit -m "Expose delegated collaboration API"
```

### Task 3: Connect React Collaboration Requests and Answers

**Files:**
- Modify: `agentmesh-demo/src/features/collaboration/api.ts`
- Modify: `agentmesh-demo/src/features/collaboration/queries.ts`
- Modify: `agentmesh-demo/src/pages/Collaboration.tsx`
- Modify: `agentmesh-demo/src/components/collaboration/HelpRequestCard.tsx`
- Modify: `agentmesh-demo/src/components/collaboration/CollabTimelineDrawer.tsx`
- Create: `agentmesh-demo/e2e/delegated-collaboration.spec.ts`

**Interfaces:**
- Consumes: Task 2 collaboration API.
- Produces: resource-ID-driven allow, decline, revoke, view-answer, and adopt interactions.

- [ ] **Step 1: Write failing delegated collaboration browser test**

```ts
import { expect, test } from '@playwright/test'

import { loginAs } from './support/auth'

test('target approves a request and asker adopts the answer', async ({ page }) => {
  await loginAs(page, 'usr_team_lead', 'lead123')
  const created = await page.request.post('/api/collaboration/requests', {
    data: { target_id: 'usr_current_designer', question: `降级预案怎么做 ${Date.now()}` },
  })
  expect(created.ok()).toBeTruthy()
  const record = (await created.json()).item

  await loginAs(page, 'usr_current_designer', 'designer123')
  await page.goto('/collaboration?tab=requests')
  const request = page.getByTestId(`delegated-request-${record.id}`)
  await expect(request).toBeVisible()
  await request.getByRole('button', { name: '允许代答' }).click()
  await expect(request.getByText('已回答')).toBeVisible()

  await loginAs(page, 'usr_team_lead', 'lead123')
  await page.goto('/collaboration?tab=mine')
  const answer = page.getByTestId(`delegated-answer-${record.id}`)
  await answer.getByRole('button', { name: '采纳答案' }).click()
  await expect(answer.getByText('已采纳')).toBeVisible()
})
```

- [ ] **Step 2: Run and verify Stage 1 has no delegated actions**

Run: `cd agentmesh-demo && npm run test:e2e -- e2e/delegated-collaboration.spec.ts`

Expected: FAIL because Stage 1 only displays market and task resources.

- [ ] **Step 3: Add server-state hooks and remove person-name branches**

```ts
export const delegatedKeys = {
  list: (direction: 'inbound' | 'outbound') => ['delegated-answers', direction] as const,
  detail: (id: string) => ['delegated-answers', id] as const,
  consents: ['delegated-consents'] as const,
}
```

`HelpRequestCard` receives `DelegatedAnswerRecord` and renders actions from status and `allowed_actions`. It never branches on a peer name. Approve and deny invalidate inbound list, detail, Inbox, and collaboration summary. Adopt invalidates outbound answers, personal memory, impact, and knowledge lineage.

Display an explicit note: the twin returns an answer with sources; it does not claim semantic privacy.

- [ ] **Step 4: Verify React collaboration and build**

Run: `cd agentmesh-demo && npm run api:types && npm run build && npm run test:e2e -- e2e/delegated-collaboration.spec.ts`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agentmesh-demo/src/features/collaboration agentmesh-demo/src/pages/Collaboration.tsx agentmesh-demo/src/components/collaboration agentmesh-demo/e2e/delegated-collaboration.spec.ts
git commit -m "Add delegated collaboration UI"
```

### Task 4: Persist Project Reviews and Emit Knowledge Candidates

**Files:**
- Modify: `agentmesh/models.py`
- Modify: `agentmesh/store.py`
- Create: `agentmesh/routes/insights.py`
- Modify: `agentmesh/app.py`
- Test: `tests/test_insights.py`

**Interfaces:**
- Consumes: current user's tasks, activity, documents, memory, and Sources.
- Produces: `ProjectReview`, insight summary, review update, candidate generation.

- [ ] **Step 1: Write failing review state-machine tests**

```python
from agentmesh.models import ProjectReviewStatus
from agentmesh.seed import PROJECT, TEAM_LEAD, USER
from tests.test_chat_flow import authenticated_client, clear_store


def test_review_requires_result_before_candidate_generation() -> None:
    clear_store()
    client = authenticated_client(USER.id)
    created = client.post("/api/insights/reviews", json={"project_id": PROJECT.id, "title": "618 项目复盘"})
    review_id = created.json()["item"]["id"]
    blocked = client.post(f"/api/insights/reviews/{review_id}/candidate")
    assert blocked.status_code == 409

    updated = client.patch(
        f"/api/insights/reviews/{review_id}",
        json={"result_text": "首屏入口调整后点击率稳定", "evidence_source_ids": []},
    )
    assert updated.json()["item"]["status"] == ProjectReviewStatus.IN_PROGRESS
    generated = client.post(f"/api/insights/reviews/{review_id}/candidate")
    assert generated.status_code == 200
    assert generated.json()["review"]["status"] == "candidate_ready"
    assert generated.json()["memory_item"]["scope"] == "team_candidate"


def test_user_cannot_read_another_users_review() -> None:
    clear_store()
    owner = authenticated_client(USER.id)
    review_id = owner.post("/api/insights/reviews", json={"project_id": PROJECT.id, "title": "private"}).json()["item"]["id"]
    assert authenticated_client(TEAM_LEAD.id).get(f"/api/insights/reviews/{review_id}").status_code == 404
```

- [ ] **Step 2: Run tests and verify route 404**

Run: `.venv/bin/python -m pytest tests/test_insights.py -v`

Expected: FAIL because review models and routes do not exist.

- [ ] **Step 3: Add explicit review model and transition commands**

```python
class ProjectReviewStatus(StrEnum):
    SUGGESTED = "suggested"
    IN_PROGRESS = "in_progress"
    MISSING_EVIDENCE = "missing_evidence"
    CANDIDATE_READY = "candidate_ready"
    COMPLETED = "completed"


class ProjectReview(BaseModel):
    id: str = Field(default_factory=lambda: new_id("review"))
    user_id: str
    workspace_id: str
    project_id: str
    title: str
    status: ProjectReviewStatus = ProjectReviewStatus.SUGGESTED
    result_text: str = ""
    evidence_source_ids: list[str] = Field(default_factory=list)
    candidate_memory_id: str | None = None
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)
```

`POST /api/insights/reviews` validates the project belongs to the user's Workspace. `PATCH` only updates the owner's result and source IDs, validates every Source exists, and sets `missing_evidence` when the result is blank. Candidate generation is idempotent, requires non-empty result text, creates one `MemoryItem` with `scope=team_candidate`, saves its ID, and returns the same result on retries.

`GET /api/insights?period=today|week|month` returns an aggregation of current-user activity, visible task cards, personal memory counts, review counts, and worker freshness. It contains facts and counts, not LLM-generated claims.

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_insights.py tests/test_chat_flow.py -k "memory or activity or task" -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agentmesh/models.py agentmesh/store.py agentmesh/routes/insights.py agentmesh/app.py tests/test_insights.py
git commit -m "Add persistent project reviews"
```

### Task 5: Connect Insights Review to the Same Knowledge Candidate

**Files:**
- Create: `agentmesh-demo/src/features/insights/api.ts`
- Create: `agentmesh-demo/src/features/insights/queries.ts`
- Modify: `agentmesh-demo/src/pages/Insights.tsx`
- Modify: `agentmesh-demo/src/components/insights/ProjectReviewDrawer.tsx`
- Modify: `agentmesh-demo/src/pages/Knowledge.tsx`
- Create: `agentmesh-demo/e2e/project-review.spec.ts`

**Interfaces:**
- Consumes: Task 4 insight and review APIs.
- Produces: one persisted review resource and one shared candidate ID across Insights and Knowledge.

- [ ] **Step 1: Write failing cross-page identity test**

```ts
import { expect, test } from '@playwright/test'

import { login } from './support/auth'

test('generated review candidate is the same resource in Knowledge', async ({ page }) => {
  await login(page)
  await page.goto('/insights')
  await page.getByRole('button', { name: '开始复盘' }).click()
  await page.getByRole('button', { name: '下一步' }).click()
  await page.getByRole('button', { name: '下一步' }).click()
  await page.getByLabel('复盘结果').fill(`验证结果 ${Date.now()}`)
  await page.getByRole('button', { name: '保存结果' }).click()
  await page.getByRole('button', { name: '生成知识候选' }).click()
  const candidateId = await page.getByTestId('candidate-id').getAttribute('data-candidate-id')
  await page.getByRole('button', { name: '前往我的知识' }).click()
  await expect(page.getByTestId(`knowledge-${candidateId}`)).toBeVisible()
})
```

- [ ] **Step 2: Run and verify local state creates no shared identity**

Run: `cd agentmesh-demo && npm run test:e2e -- e2e/project-review.spec.ts`

Expected: FAIL because the current review uses a timer and Knowledge uses a different static object.

- [ ] **Step 3: Replace local review state with server resources**

`ProjectReviewDrawer` receives `reviewId`. Each step reads the canonical review. Saving result calls PATCH; candidate generation calls the idempotent candidate command. Remove `setTimeout`, `ReviewStatus` local state, and `KnowledgeCandidateStatus` local state.

```ts
export const reviewKeys = {
  insights: (period: 'today' | 'week' | 'month') => ['insights', period] as const,
  list: ['project-reviews'] as const,
  detail: (id: string) => ['project-reviews', id] as const,
}
```

After candidate generation, invalidate review detail, review list, insight summary, knowledge overview, and bootstrap metrics. Navigate to `/knowledge?candidate=<memory_id>` so Knowledge highlights the same returned resource.

- [ ] **Step 4: Verify browser and backend**

Run: `cd agentmesh-demo && npm run api:types && npm run build && npm run test:e2e -- e2e/project-review.spec.ts`

Run: `.venv/bin/python -m pytest tests/test_insights.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agentmesh-demo/src/features/insights agentmesh-demo/src/pages/Insights.tsx agentmesh-demo/src/components/insights agentmesh-demo/src/pages/Knowledge.tsx agentmesh-demo/e2e/project-review.spec.ts
git commit -m "Connect project reviews to knowledge"
```

### Task 6: Persist Digital Understanding and User Preferences

**Files:**
- Modify: `agentmesh/models.py`
- Modify: `agentmesh/store.py`
- Create: `agentmesh/routes/profile.py`
- Modify: `agentmesh/app.py`
- Test: `tests/test_profile.py`

**Interfaces:**
- Consumes: current user and existing audit seam.
- Produces: understanding list/update, preference read/update, impact summary.

- [ ] **Step 1: Write failing current-user scope tests**

```python
from agentmesh.seed import TEAM_LEAD, USER
from tests.test_chat_flow import authenticated_client, clear_store


def test_understanding_update_is_current_user_scoped() -> None:
    clear_store()
    user = authenticated_client(USER.id)
    created = user.post("/api/profile/understandings", json={"text": "偏好效率优先"})
    item_id = created.json()["item"]["id"]
    assert authenticated_client(TEAM_LEAD.id).patch(
        f"/api/profile/understandings/{item_id}", json={"status": "confirmed"}
    ).status_code == 404
    updated = user.patch(
        f"/api/profile/understandings/{item_id}", json={"status": "modified", "text": "偏好入口效率优先"}
    )
    assert updated.json()["item"]["status"] == "modified"


def test_impact_is_derived_from_persisted_records() -> None:
    clear_store()
    response = authenticated_client(USER.id).get("/api/profile/impact")
    assert response.status_code == 200
    assert set(response.json()) == {
        "active_consent_count",
        "people_helped",
        "project_count",
        "monthly_adoptions",
        "events",
    }
```

- [ ] **Step 2: Run tests and verify missing profile route**

Run: `.venv/bin/python -m pytest tests/test_profile.py -v`

Expected: FAIL with 404.

- [ ] **Step 3: Add profile models and current-user routes**

```python
class UnderstandingStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    MODIFIED = "modified"
    IGNORED = "ignored"


class AgentUnderstanding(BaseModel):
    id: str = Field(default_factory=lambda: new_id("understanding"))
    user_id: str
    text: str = Field(min_length=1, max_length=500)
    status: UnderstandingStatus = UnderstandingStatus.PENDING
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class UserPreference(BaseModel):
    id: str
    user_id: str
    theme: str = Field(default="dark", pattern="^dark$")
    confirm_new_knowledge: bool = True
    updated_at: datetime = Field(default_factory=now_utc)
```

Understanding create/update always binds `user_id` to the session. Modified status requires replacement text. Preferences support only fields the server persists; theme remains dark until a second real theme exists.

Impact is a read model. `active_consent_count` counts active grants where the current user is grantor; `people_helped` counts unique `ContributionPoint.awarded_by_id` values for points awarded to the current user; `project_count` counts distinct non-null project IDs in the current user's personal memory; `monthly_adoptions` counts current-month contribution points; events come from audit actions where the user is actor, target, `awarded_to`, asker, or target. Do not persist duplicated counters or infer ownership of legacy `MemoryItem` rows.

- [ ] **Step 4: Run tests and lint**

Run: `.venv/bin/python -m pytest tests/test_profile.py tests/test_delegated_answer.py tests/test_chat_flow.py -k "memory" -v`

Run: `.venv/bin/ruff check agentmesh tests/test_profile.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agentmesh/models.py agentmesh/store.py agentmesh/routes/profile.py agentmesh/app.py tests/test_profile.py
git commit -m "Add digital profile state"
```

### Task 7: Connect Digital Self, Impact, and Settings

**Files:**
- Create: `agentmesh-demo/src/features/digital-self/api.ts`
- Create: `agentmesh-demo/src/features/digital-self/queries.ts`
- Modify: `agentmesh-demo/src/components/digital-self/UnderstandingList.tsx`
- Modify: `agentmesh-demo/src/components/digital-self/MyImpact.tsx`
- Modify: `agentmesh-demo/src/components/layout/ProfileDrawer.tsx`
- Create: `agentmesh-demo/src/features/settings/api.ts`
- Modify: `agentmesh-demo/src/components/layout/SettingsDrawer.tsx`
- Create: `agentmesh-demo/e2e/digital-profile.spec.ts`

**Interfaces:**
- Consumes: Task 6 profile API.
- Produces: canonical understanding updates, derived impact, persisted settings.

- [ ] **Step 1: Write failing profile browser test**

```ts
import { expect, test } from '@playwright/test'

import { login } from './support/auth'

test('understanding confirmation survives reload and impact stays server-derived', async ({ page }) => {
  await login(page)
  const created = await page.request.post('/api/profile/understandings', {
    data: { text: `偏好入口效率优先 ${Date.now()}` },
  })
  expect(created.ok()).toBeTruthy()
  const item = (await created.json()).item
  await page.goto('/digital-self')
  const pending = page.getByTestId(`understanding-${item.id}`)
  await pending.getByRole('button', { name: '确认' }).click()
  await expect(pending.getByText('已确认')).toBeVisible()
  await page.reload()
  await expect(page.getByTestId(`understanding-${item.id}`).getByText('已确认')).toBeVisible()
  await expect(page.getByTestId('impact-active-consents')).toHaveAttribute('data-source', 'server')
})
```

- [ ] **Step 2: Run and verify DemoContext state is gone or non-persistent**

Run: `cd agentmesh-demo && npm run test:e2e -- e2e/digital-profile.spec.ts`

Expected: FAIL because Stage 1 hides unsupported understanding actions and has no impact endpoint.

- [ ] **Step 3: Add profile queries and canonical mutations**

```ts
export const profileKeys = {
  understandings: ['profile', 'understandings'] as const,
  impact: ['profile', 'impact'] as const,
  preferences: ['profile', 'preferences'] as const,
}
```

`UnderstandingList` renders server items and submits `confirmed`, `modified`, or `ignored`; only modified opens an input and sends replacement text. `MyImpact` renders effective grants, helped colleagues, project coverage, monthly adoptions, and audit events without incrementing anything locally. Settings renders only `confirm_new_knowledge` and the actual dark theme state; it removes decorative controls without a server field.

- [ ] **Step 4: Run profile browser flow and full build**

Run: `cd agentmesh-demo && npm run api:types && npm run build && npm run test:e2e -- e2e/digital-profile.spec.ts`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agentmesh-demo/src/features/digital-self agentmesh-demo/src/features/settings agentmesh-demo/src/components/digital-self agentmesh-demo/src/components/layout/ProfileDrawer.tsx agentmesh-demo/src/components/layout/SettingsDrawer.tsx agentmesh-demo/e2e/digital-profile.spec.ts
git commit -m "Connect digital profile capabilities"
```

### Task 8: Run the Stage 2 Release Gate

**Files:**
- Modify: `README.md`
- Modify: `CONTEXT.md`
- Create: `agentmesh-demo/e2e/stage-2-parity.spec.ts`

**Interfaces:**
- Consumes: Tasks 1 through 7.
- Produces: documented, verified Stage 2 behavior.

- [ ] **Step 1: Add the final cross-feature browser test**

```ts
import { expect, test } from '@playwright/test'

import { login } from './support/auth'

test('stage 2 pages contain no local demo state', async ({ page }) => {
  await login(page)
  for (const route of ['/digital-self', '/insights', '/knowledge', '/collaboration']) {
    await page.goto(route)
    await expect(page.locator('body')).not.toContainText('模拟生成')
    await expect(page.locator('body')).not.toContainText('演示 Mock')
  }
})
```

- [ ] **Step 2: Run the release gate**

Run:

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check .
cd agentmesh-demo
npm run api:types
npm run build
npm run test:e2e
```

Expected: all backend tests PASS, Ruff PASS, TypeScript/Vite build PASS, all Playwright flows PASS.

- [ ] **Step 3: Update product reality docs**

Update `CONTEXT.md` so delegated answer, consent, shadow contribution, lineage, project review, understanding, impact, and preferences reflect current code. Keep these limits explicit: answer-only is not semantic privacy, points are not redeemable, review candidates still require governance, and there is no real-time transport.

Update README API snapshot with the new collaboration, insights, and profile routes. Include no API keys, OAuth secrets, O2 tokens, or production credentials.

- [ ] **Step 4: Verify docs contain no stale absence claims**

Run: `.venv/bin/python -m pytest tests/test_collaboration_api.py tests/test_insights.py tests/test_profile.py -v`

Expected: PASS.

Search `CONTEXT.md` for claims that delegated answer, contribution, lineage, review, understanding, or preferences are absent and remove any contradicted statement.

- [ ] **Step 5: Commit**

```bash
git add README.md CONTEXT.md agentmesh-demo/e2e/stage-2-parity.spec.ts
git commit -m "Document complete AgentMesh product flow"
```

## Stage 2 Completion Gate

- Every collaboration request, answer, review, understanding, and preference has a stable server resource ID.
- Approve, deny, adopt, candidate generation, and understanding updates survive reload.
- Insights and Knowledge reference the same candidate memory ID.
- Impact numbers are derived from persisted records and audits.
- High-sensitivity delegated answers remain gated.
- Adoption is idempotent.
- No local business counters, name-based branches, fake timers, or static domain records remain.
