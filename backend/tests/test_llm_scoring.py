import pytest
from sqlalchemy import text

import app.services.check_service as check_service
from app.services.llm.client import LLMCallResult, LLMOutputError
from app.services.llm.provider_nim import _extract_json
from app.services.llm.scoring import MaterialityResult


def test_extract_json_handles_markdown_fences():
    text = '```json\n{"score": 80, "classification": "pricing_move", "rationale": "x"}\n```'
    assert _extract_json(text) == '{"score": 80, "classification": "pricing_move", "rationale": "x"}'


def test_extract_json_raises_when_no_object_present():
    with pytest.raises(LLMOutputError):
        _extract_json("no json here")


class _FakeLLMClient:
    def __init__(self, materiality_result: MaterialityResult):
        self._materiality_result = materiality_result

    def complete(self, system, user, response_model):
        assert response_model is MaterialityResult
        return LLMCallResult(
            value=self._materiality_result,
            model="fake-model",
            prompt_tokens=42,
            completion_tokens=7,
        )

    def embed(self, texts):
        raise NotImplementedError


def _register_login_and_workspace(client, email):
    client.post(
        "/auth/register",
        json={"email": email, "password": "supersecret1", "full_name": email.split("@")[0]},
    )
    login_res = client.post("/auth/login", json={"email": email, "password": "supersecret1"})
    headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}
    workspace = client.post("/workspaces/", json={"name": "Acme PMM"}, headers=headers).json()
    return headers, workspace["id"]


def test_check_populates_materiality_when_llm_configured(client, monkeypatch, db_session):
    headers, workspace_id = _register_login_and_workspace(client, "alice@example.com")
    competitor = client.post(
        f"/workspaces/{workspace_id}/competitors/", json={"name": "Rival"}, headers=headers
    ).json()
    surface = client.post(
        f"/workspaces/{workspace_id}/competitors/{competitor['id']}/surfaces/",
        json={"surface_type": "pricing", "url": "https://rival.example.com", "check_frequency": "daily"},
        headers=headers,
    ).json()
    check_url = (
        f"/workspaces/{workspace_id}/competitors/{competitor['id']}"
        f"/surfaces/{surface['id']}/check"
    )

    monkeypatch.setattr(check_service, "capture_clean_snapshot", lambda url: "Plan A $10")
    client.post(check_url, headers=headers)

    fake_result = MaterialityResult(
        score=87, classification="pricing_move", rationale="They raised Plan A by $5."
    )
    monkeypatch.setattr(check_service, "get_llm_client", lambda: _FakeLLMClient(fake_result))
    monkeypatch.setattr(check_service, "capture_clean_snapshot", lambda url: "Plan A $15")

    changed_res = client.post(check_url, headers=headers)
    assert changed_res.json()["status"] == "change_detected"

    logs = client.get(f"/workspaces/{workspace_id}/change-logs/", headers=headers).json()
    assert len(logs) == 1
    assert logs[0]["materiality_score"] == 87
    assert logs[0]["classification"] == "pricing_move"
    assert logs[0]["rationale"] == "They raised Plan A by $5."

    usage_rows = db_session.execute(
        text("SELECT purpose, model, prompt_tokens FROM token_usage_logs")
    ).fetchall()
    assert len(usage_rows) == 1
    assert usage_rows[0][1] == "fake-model"
    assert usage_rows[0][2] == 42


def test_check_leaves_change_log_unscored_when_no_llm_configured(client, monkeypatch):
    headers, workspace_id = _register_login_and_workspace(client, "bob@example.com")
    competitor = client.post(
        f"/workspaces/{workspace_id}/competitors/", json={"name": "Rival"}, headers=headers
    ).json()
    surface = client.post(
        f"/workspaces/{workspace_id}/competitors/{competitor['id']}/surfaces/",
        json={"surface_type": "pricing", "url": "https://rival.example.com", "check_frequency": "daily"},
        headers=headers,
    ).json()
    check_url = (
        f"/workspaces/{workspace_id}/competitors/{competitor['id']}"
        f"/surfaces/{surface['id']}/check"
    )

    monkeypatch.setattr(check_service, "get_llm_client", lambda: None)
    monkeypatch.setattr(check_service, "capture_clean_snapshot", lambda url: "Plan A $10")
    client.post(check_url, headers=headers)
    monkeypatch.setattr(check_service, "capture_clean_snapshot", lambda url: "Plan A $15")
    client.post(check_url, headers=headers)

    logs = client.get(f"/workspaces/{workspace_id}/change-logs/", headers=headers).json()
    assert len(logs) == 1
    assert logs[0]["materiality_score"] is None
    assert logs[0]["classification"] is None


def test_check_survives_llm_failure(client, monkeypatch):
    headers, workspace_id = _register_login_and_workspace(client, "carol@example.com")
    competitor = client.post(
        f"/workspaces/{workspace_id}/competitors/", json={"name": "Rival"}, headers=headers
    ).json()
    surface = client.post(
        f"/workspaces/{workspace_id}/competitors/{competitor['id']}/surfaces/",
        json={"surface_type": "pricing", "url": "https://rival.example.com", "check_frequency": "daily"},
        headers=headers,
    ).json()
    check_url = (
        f"/workspaces/{workspace_id}/competitors/{competitor['id']}"
        f"/surfaces/{surface['id']}/check"
    )

    class _BrokenLLMClient:
        def complete(self, system, user, response_model):
            raise LLMOutputError("boom")

        def embed(self, texts):
            raise NotImplementedError

    monkeypatch.setattr(check_service, "capture_clean_snapshot", lambda url: "Plan A $10")
    client.post(check_url, headers=headers)

    monkeypatch.setattr(check_service, "get_llm_client", lambda: _BrokenLLMClient())
    monkeypatch.setattr(check_service, "capture_clean_snapshot", lambda url: "Plan A $15")
    changed_res = client.post(check_url, headers=headers)

    # The check itself must still succeed even though scoring failed.
    assert changed_res.status_code == 200
    assert changed_res.json()["status"] == "change_detected"
