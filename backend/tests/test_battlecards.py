import app.routers.battlecards as battlecards_router
from app.services.llm.client import LLMCallResult
from app.services.battlecard_service import BattlecardDraft


class _FakeBattlecardLLMClient:
    def __init__(self, summary="Rival raised pricing.", content="## Their move\nRaised pricing.\n## Our counter\nEmphasize value."):
        self._summary = summary
        self._content = content

    def complete(self, system, user, response_model):
        assert response_model is BattlecardDraft
        return LLMCallResult(
            value=BattlecardDraft(change_summary=self._summary, updated_content_markdown=self._content),
            model="fake-model", prompt_tokens=30, completion_tokens=15,
        )

    def embed(self, texts):
        raise NotImplementedError


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
                value=MaterialityResult(score=85, classification="positioning_shift", rationale="Repositioning."),
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

    return workspace, competitor, check_res["change_log_id"]


def test_get_battlecard_404_before_any_update(client, monkeypatch):
    owner_headers = _register_login(client, "owner@example.com")
    workspace, competitor, _ = _seed_workspace_with_scored_change(client, owner_headers, monkeypatch)

    res = client.get(
        f"/workspaces/{workspace['id']}/competitors/{competitor['id']}/battlecard/", headers=owner_headers
    )
    assert res.status_code == 404


def test_propose_and_approve_update_creates_and_bumps_battlecard(client, monkeypatch):
    owner_headers = _register_login(client, "owner@example.com")
    workspace, competitor, change_log_id = _seed_workspace_with_scored_change(client, owner_headers, monkeypatch)
    monkeypatch.setattr(battlecards_router, "get_llm_client", lambda: _FakeBattlecardLLMClient())

    propose_res = client.post(
        f"/workspaces/{workspace['id']}/competitors/{competitor['id']}/battlecard/updates",
        json={"change_log_ids": [change_log_id]},
        headers=owner_headers,
    )
    assert propose_res.status_code == 200
    update = propose_res.json()
    assert update["status"] == "pending"

    approvals = client.get(
        f"/workspaces/{workspace['id']}/approvals/?status=pending", headers=owner_headers
    ).json()
    battlecard_approval = next(a for a in approvals if a["item_type"] == "battlecard_update")

    approve_res = client.post(
        f"/workspaces/{workspace['id']}/approvals/{battlecard_approval['id']}/approve",
        json={}, headers=owner_headers,
    )
    assert approve_res.status_code == 200

    battlecard = client.get(
        f"/workspaces/{workspace['id']}/competitors/{competitor['id']}/battlecard/", headers=owner_headers
    ).json()
    assert battlecard["version"] == 1
    assert "Their move" in battlecard["content_markdown"]

    updates = client.get(
        f"/workspaces/{workspace['id']}/competitors/{competitor['id']}/battlecard/updates", headers=owner_headers
    ).json()
    assert updates[0]["status"] == "approved"


def test_rejected_update_does_not_change_battlecard(client, monkeypatch):
    owner_headers = _register_login(client, "owner@example.com")
    workspace, competitor, change_log_id = _seed_workspace_with_scored_change(client, owner_headers, monkeypatch)
    monkeypatch.setattr(battlecards_router, "get_llm_client", lambda: _FakeBattlecardLLMClient())

    client.post(
        f"/workspaces/{workspace['id']}/competitors/{competitor['id']}/battlecard/updates",
        json={"change_log_ids": [change_log_id]},
        headers=owner_headers,
    )
    approvals = client.get(
        f"/workspaces/{workspace['id']}/approvals/?status=pending", headers=owner_headers
    ).json()
    battlecard_approval = approvals[0]

    client.post(
        f"/workspaces/{workspace['id']}/approvals/{battlecard_approval['id']}/reject",
        json={}, headers=owner_headers,
    )

    # Proposing an update creates the empty Battlecard shell immediately
    # (so there's something to attach the proposed diff to), but a rejected
    # update must never write its content into it — version stays at 0.
    battlecard = client.get(
        f"/workspaces/{workspace['id']}/competitors/{competitor['id']}/battlecard/", headers=owner_headers
    ).json()
    assert battlecard["version"] == 0
    assert battlecard["content_markdown"] == ""

    updates = client.get(
        f"/workspaces/{workspace['id']}/competitors/{competitor['id']}/battlecard/updates", headers=owner_headers
    ).json()
    assert updates[0]["status"] == "rejected"


def test_second_update_bumps_version_again(client, monkeypatch):
    owner_headers = _register_login(client, "owner@example.com")
    workspace, competitor, change_log_id = _seed_workspace_with_scored_change(client, owner_headers, monkeypatch)

    monkeypatch.setattr(battlecards_router, "get_llm_client", lambda: _FakeBattlecardLLMClient("first", "v1 content"))
    client.post(
        f"/workspaces/{workspace['id']}/competitors/{competitor['id']}/battlecard/updates",
        json={"change_log_ids": [change_log_id]}, headers=owner_headers,
    )
    approval_1 = client.get(
        f"/workspaces/{workspace['id']}/approvals/?status=pending", headers=owner_headers
    ).json()[0]
    client.post(
        f"/workspaces/{workspace['id']}/approvals/{approval_1['id']}/approve", json={}, headers=owner_headers
    )

    monkeypatch.setattr(battlecards_router, "get_llm_client", lambda: _FakeBattlecardLLMClient("second", "v2 content"))
    client.post(
        f"/workspaces/{workspace['id']}/competitors/{competitor['id']}/battlecard/updates",
        json={"change_log_ids": [change_log_id]}, headers=owner_headers,
    )
    approval_2 = client.get(
        f"/workspaces/{workspace['id']}/approvals/?status=pending", headers=owner_headers
    ).json()[0]
    client.post(
        f"/workspaces/{workspace['id']}/approvals/{approval_2['id']}/approve", json={}, headers=owner_headers
    )

    battlecard = client.get(
        f"/workspaces/{workspace['id']}/competitors/{competitor['id']}/battlecard/", headers=owner_headers
    ).json()
    assert battlecard["version"] == 2
    assert battlecard["content_markdown"] == "v2 content"


def test_response_library_crud_and_tag_filter(client, monkeypatch):
    owner_headers = _register_login(client, "owner@example.com")
    workspace, competitor, _ = _seed_workspace_with_scored_change(client, owner_headers, monkeypatch)

    create_res = client.post(
        f"/workspaces/{workspace['id']}/response-library/",
        json={
            "competitor_id": competitor["id"],
            "title": "Pricing objection handler",
            "body_markdown": "When asked about their lower price, say...",
            "tags": ["pricing", "objection-handling"],
        },
        headers=owner_headers,
    )
    assert create_res.status_code == 200
    item = create_res.json()

    other_res = client.post(
        f"/workspaces/{workspace['id']}/response-library/",
        json={"title": "General positioning", "body_markdown": "We are the only...", "tags": ["positioning"]},
        headers=owner_headers,
    )
    assert other_res.status_code == 200

    all_items = client.get(
        f"/workspaces/{workspace['id']}/response-library/", headers=owner_headers
    ).json()
    assert len(all_items) == 2

    tagged = client.get(
        f"/workspaces/{workspace['id']}/response-library/?tag=pricing", headers=owner_headers
    ).json()
    assert len(tagged) == 1
    assert tagged[0]["id"] == item["id"]

    update_res = client.patch(
        f"/workspaces/{workspace['id']}/response-library/{item['id']}",
        json={"title": "Updated title"},
        headers=owner_headers,
    )
    assert update_res.json()["title"] == "Updated title"

    delete_res = client.delete(
        f"/workspaces/{workspace['id']}/response-library/{item['id']}", headers=owner_headers
    )
    assert delete_res.status_code == 200

    remaining = client.get(
        f"/workspaces/{workspace['id']}/response-library/", headers=owner_headers
    ).json()
    assert len(remaining) == 1


def test_reviewer_cannot_create_response_library_item(client, monkeypatch):
    owner_headers = _register_login(client, "owner@example.com")
    reviewer_headers = _register_login(client, "reviewer@example.com")
    workspace, competitor, _ = _seed_workspace_with_scored_change(client, owner_headers, monkeypatch)

    client.post(
        f"/workspaces/{workspace['id']}/members",
        json={"email": "reviewer@example.com", "role": "reviewer"},
        headers=owner_headers,
    )

    res = client.post(
        f"/workspaces/{workspace['id']}/response-library/",
        json={"title": "x", "body_markdown": "y"},
        headers=reviewer_headers,
    )
    assert res.status_code == 403
