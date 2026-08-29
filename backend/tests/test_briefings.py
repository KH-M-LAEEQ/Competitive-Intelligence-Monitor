import app.routers.briefings as briefings_router
import app.services.briefing_service as briefing_service
from app.models.briefing import BriefingStatus
from app.models.approval_item import ApprovalStatus
from app.services.llm.client import LLMCallResult
from app.services.briefing_service import BriefingDraft


class _FakeBriefingLLMClient:
    def complete(self, system, user, response_model):
        assert response_model is BriefingDraft
        return LLMCallResult(
            value=BriefingDraft(
                title="Rival raises entry pricing",
                body_markdown="Rival A increased their entry-tier price by 50%.",
            ),
            model="fake-model", prompt_tokens=50, completion_tokens=20,
        )

    def embed(self, texts):
        raise NotImplementedError


def _fake_briefing_llm(monkeypatch, client=None):
    # generate-now (router) checks get_llm_client() up front to reject with
    # 400 before creating a job; run_briefing_job (service, background task)
    # resolves get_llm_client() again independently when it actually
    # generates content. Each module bound its own name to the factory
    # function at import time, so both need patching separately — patching
    # only the router's leaves the background job calling the real LLM.
    fake = client or _FakeBriefingLLMClient()
    monkeypatch.setattr(briefings_router, "get_llm_client", lambda: fake)
    monkeypatch.setattr(briefing_service, "get_llm_client", lambda: fake)


def _register_login(client, email):
    client.post(
        "/auth/register",
        json={"email": email, "password": "supersecret1", "full_name": email.split("@")[0]},
    )
    res = client.post("/auth/login", json={"email": email, "password": "supersecret1"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _seed_workspace_with_scored_change(client, owner_headers, monkeypatch):
    workspace = client.post("/workspaces/", json={"name": "Acme"}, headers=owner_headers).json()
    competitor = client.post(
        f"/workspaces/{workspace['id']}/competitors/", json={"name": "Rival"}, headers=owner_headers
    ).json()
    surface = client.post(
        f"/workspaces/{workspace['id']}/competitors/{competitor['id']}/surfaces/",
        json={"surface_type": "pricing", "url": "https://rival.example.com", "check_frequency": "daily"},
        headers=owner_headers,
    ).json()

    import app.services.check_service as check_service

    class _ScoringClient:
        def complete(self, system, user, response_model):
            from app.services.llm.scoring import MaterialityResult
            return LLMCallResult(
                value=MaterialityResult(score=85, classification="pricing_move", rationale="Price hike."),
                model="fake-model", prompt_tokens=10, completion_tokens=5,
            )

        def embed(self, texts):
            from app.services.llm.client import EmbedResult
            return EmbedResult(vectors=[[0.1, 0.2]], model="fake-embed", prompt_tokens=2)

    check_url = f"/workspaces/{workspace['id']}/competitors/{competitor['id']}/surfaces/{surface['id']}/check"
    monkeypatch.setattr(check_service, "capture_clean_snapshot", lambda url: "Plan A $10")
    client.post(check_url, headers=owner_headers)
    monkeypatch.setattr(check_service, "get_llm_client", lambda: _ScoringClient())
    monkeypatch.setattr(check_service, "capture_clean_snapshot", lambda url: "Plan A $15")
    check_res = client.post(check_url, headers=owner_headers).json()

    return workspace, check_res["change_log_id"]


def test_generate_briefing_creates_pending_approval(client, monkeypatch):
    owner_headers = _register_login(client, "owner@example.com")
    workspace, change_log_id = _seed_workspace_with_scored_change(client, owner_headers, monkeypatch)

    _fake_briefing_llm(monkeypatch)

    res = client.post(
        f"/workspaces/{workspace['id']}/briefings/generate-now",
        json={"audience": "sales", "digest_type": "urgent", "change_log_ids": [change_log_id]},
        headers=owner_headers,
    )
    assert res.status_code == 202
    job = res.json()
    assert job["status"] in ("queued", "running", "success")

    # BackgroundTasks run after the response is sent, not necessarily
    # resolved by the time res.json() is parsed — a follow-up request gives
    # the event loop a chance to finish it.
    job_res = client.get(
        f"/workspaces/{workspace['id']}/briefings/jobs/{job['id']}", headers=owner_headers
    ).json()
    assert job_res["status"] == "success"
    assert job_res["briefing_id"] is not None

    briefing = client.get(
        f"/workspaces/{workspace['id']}/briefings/{job_res['briefing_id']}", headers=owner_headers
    ).json()
    assert briefing["status"] == "pending_approval"
    assert briefing["title"] == "Rival raises entry pricing"

    approvals = client.get(
        f"/workspaces/{workspace['id']}/approvals/?status=pending", headers=owner_headers
    ).json()
    assert len(approvals) == 1
    assert approvals[0]["item_type"] == "briefing"
    assert approvals[0]["item_id"] == briefing["id"]


def test_generate_briefing_rejects_change_logs_outside_workspace(client, monkeypatch):
    owner_headers = _register_login(client, "owner@example.com")
    workspace, _ = _seed_workspace_with_scored_change(client, owner_headers, monkeypatch)
    _fake_briefing_llm(monkeypatch)

    res = client.post(
        f"/workspaces/{workspace['id']}/briefings/generate-now",
        json={"audience": "all", "digest_type": "urgent", "change_log_ids": [999999]},
        headers=owner_headers,
    )
    # change_log_ids aren't validated until the background job actually
    # runs generate_briefing() — the request itself is just queued.
    assert res.status_code == 202
    job = res.json()

    job_res = client.get(
        f"/workspaces/{workspace['id']}/briefings/jobs/{job['id']}", headers=owner_headers
    ).json()
    assert job_res["status"] == "failed"
    assert job_res["briefing_id"] is None


def test_approve_flow_updates_briefing_and_writes_audit_log(client, monkeypatch):
    owner_headers = _register_login(client, "owner@example.com")
    workspace, change_log_id = _seed_workspace_with_scored_change(client, owner_headers, monkeypatch)
    _fake_briefing_llm(monkeypatch)

    job = client.post(
        f"/workspaces/{workspace['id']}/briefings/generate-now",
        json={"audience": "all", "digest_type": "urgent", "change_log_ids": [change_log_id]},
        headers=owner_headers,
    ).json()
    briefing_id = client.get(
        f"/workspaces/{workspace['id']}/briefings/jobs/{job['id']}", headers=owner_headers
    ).json()["briefing_id"]
    approval = client.get(
        f"/workspaces/{workspace['id']}/approvals/", headers=owner_headers
    ).json()[0]

    approve_res = client.post(
        f"/workspaces/{workspace['id']}/approvals/{approval['id']}/approve",
        json={"notes": "looks right"},
        headers=owner_headers,
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "approved"

    briefing_after = client.get(
        f"/workspaces/{workspace['id']}/briefings/{briefing_id}", headers=owner_headers
    ).json()
    assert briefing_after["status"] == "approved"

    audit = client.get(f"/workspaces/{workspace['id']}/audit-log/", headers=owner_headers).json()
    assert len(audit) == 1
    assert audit[0]["action"] == "approval.approved"
    assert audit[0]["entity_type"] == "briefing"
    assert audit[0]["extra_data"] == {"notes": "looks right"}


def test_cannot_decide_the_same_approval_twice(client, monkeypatch):
    owner_headers = _register_login(client, "owner@example.com")
    workspace, change_log_id = _seed_workspace_with_scored_change(client, owner_headers, monkeypatch)
    _fake_briefing_llm(monkeypatch)

    client.post(
        f"/workspaces/{workspace['id']}/briefings/generate-now",
        json={"audience": "all", "digest_type": "urgent", "change_log_ids": [change_log_id]},
        headers=owner_headers,
    )
    approval = client.get(
        f"/workspaces/{workspace['id']}/approvals/", headers=owner_headers
    ).json()[0]

    client.post(
        f"/workspaces/{workspace['id']}/approvals/{approval['id']}/approve",
        json={}, headers=owner_headers,
    )
    second_res = client.post(
        f"/workspaces/{workspace['id']}/approvals/{approval['id']}/reject",
        json={}, headers=owner_headers,
    )
    assert second_res.status_code == 400


def test_editor_cannot_approve_only_owner_and_reviewer_can(client, monkeypatch):
    owner_headers = _register_login(client, "owner2@example.com")
    editor_headers = _register_login(client, "editor2@example.com")
    workspace, change_log_id = _seed_workspace_with_scored_change(client, owner_headers, monkeypatch)

    client.post(
        f"/workspaces/{workspace['id']}/members",
        json={"email": "editor2@example.com", "role": "editor"},
        headers=owner_headers,
    )

    _fake_briefing_llm(monkeypatch)
    client.post(
        f"/workspaces/{workspace['id']}/briefings/generate-now",
        json={"audience": "all", "digest_type": "urgent", "change_log_ids": [change_log_id]},
        headers=owner_headers,
    )
    approval = client.get(
        f"/workspaces/{workspace['id']}/approvals/", headers=owner_headers
    ).json()[0]

    forbidden_res = client.post(
        f"/workspaces/{workspace['id']}/approvals/{approval['id']}/approve",
        json={}, headers=editor_headers,
    )
    assert forbidden_res.status_code == 403

    allowed_res = client.post(
        f"/workspaces/{workspace['id']}/approvals/{approval['id']}/approve",
        json={}, headers=owner_headers,
    )
    assert allowed_res.status_code == 200
