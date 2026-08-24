from datetime import datetime, timedelta

import pytest

import app.services.check_service as check_service
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember, WorkspaceRole
from app.models.user import User
from app.models.competitor import Competitor
from app.models.surface import Surface, SurfaceType
from app.models.change_log import ChangeLog
from app.models.change_embedding import ChangeEmbedding
from app.services.llm.client import LLMCallResult
from app.services.synthesis import (
    _cosine_similarity,
    find_similar_changes,
    generate_cross_competitor_summary,
    SynthesisResult,
)


def test_cosine_similarity_identical_vectors_is_one():
    assert _cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal_vectors_is_zero():
    assert _cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_cosine_similarity_opposite_vectors_is_negative_one():
    assert _cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)


def _seed_workspace_with_changes(db_session):
    user = User(email="alice@example.com", hashed_password="x", full_name="Alice")
    db_session.add(user)
    db_session.flush()

    workspace = Workspace(name="Acme", slug="acme")
    db_session.add(workspace)
    db_session.flush()

    db_session.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role=WorkspaceRole.owner))

    competitor_a = Competitor(name="Rival A", workspace_id=workspace.id, created_by_user_id=user.id)
    competitor_b = Competitor(name="Rival B", workspace_id=workspace.id, created_by_user_id=user.id)
    db_session.add_all([competitor_a, competitor_b])
    db_session.flush()

    surface_a = Surface(competitor_id=competitor_a.id, surface_type=SurfaceType.pricing, url="https://a.example.com")
    surface_b = Surface(competitor_id=competitor_b.id, surface_type=SurfaceType.pricing, url="https://b.example.com")
    db_session.add_all([surface_a, surface_b])
    db_session.flush()

    cl1 = ChangeLog(
        competitor_id=competitor_a.id, surface_id=surface_a.id, new_snapshot_id=1,
        diff="Plan A: $10 -> $15", classification="pricing_move",
        rationale="Rival A raised entry pricing.", materiality_score=80,
    )
    cl2 = ChangeLog(
        competitor_id=competitor_b.id, surface_id=surface_b.id, new_snapshot_id=1,
        diff="Plan A: $12 -> $18", classification="pricing_move",
        rationale="Rival B also raised entry pricing.", materiality_score=75,
    )
    cl3 = ChangeLog(
        competitor_id=competitor_b.id, surface_id=surface_b.id, new_snapshot_id=1,
        diff="Added dark mode", classification="new_feature",
        rationale="Rival B shipped dark mode.", materiality_score=40,
    )
    db_session.add_all([cl1, cl2, cl3])
    db_session.flush()

    db_session.add_all([
        ChangeEmbedding(change_log_id=cl1.id, workspace_id=workspace.id, vector=[1.0, 0.0, 0.0], model="fake"),
        ChangeEmbedding(change_log_id=cl2.id, workspace_id=workspace.id, vector=[0.99, 0.01, 0.0], model="fake"),
        ChangeEmbedding(change_log_id=cl3.id, workspace_id=workspace.id, vector=[0.0, 0.0, 1.0], model="fake"),
    ])
    db_session.commit()

    return workspace, cl1, cl2, cl3


def test_find_similar_changes_ranks_by_cosine_similarity(db_session):
    workspace, cl1, cl2, cl3 = _seed_workspace_with_changes(db_session)

    results = find_similar_changes(db_session, workspace.id, cl1.id, top_k=5)

    assert [r.change_log.id for r in results] == [cl2.id, cl3.id]
    assert results[0].similarity > results[1].similarity


def test_find_similar_changes_returns_empty_when_no_embedding(db_session):
    workspace, cl1, cl2, cl3 = _seed_workspace_with_changes(db_session)
    assert find_similar_changes(db_session, workspace.id, 999999) == []


class _FakeSynthesisLLMClient:
    def __init__(self, summary: str):
        self._summary = summary

    def complete(self, system, user, response_model):
        assert response_model is SynthesisResult
        return LLMCallResult(
            value=SynthesisResult(summary=self._summary),
            model="fake-model", prompt_tokens=10, completion_tokens=5,
        )

    def embed(self, texts):
        raise NotImplementedError


def test_generate_cross_competitor_summary_returns_outcome(db_session):
    workspace, cl1, cl2, cl3 = _seed_workspace_with_changes(db_session)
    llm_client = _FakeSynthesisLLMClient("Two rivals raised entry pricing this week.")

    since = datetime.utcnow() - timedelta(days=14)
    outcome = generate_cross_competitor_summary(db_session, llm_client, workspace.id, since)

    assert outcome is not None
    assert outcome.summary == "Two rivals raised entry pricing this week."
    assert outcome.based_on == 3


def test_generate_cross_competitor_summary_returns_none_when_no_scored_changes(db_session):
    user = User(email="bob@example.com", hashed_password="x", full_name="Bob")
    db_session.add(user)
    db_session.flush()
    workspace = Workspace(name="Empty Co", slug="empty-co")
    db_session.add(workspace)
    db_session.commit()

    outcome = generate_cross_competitor_summary(
        db_session, _FakeSynthesisLLMClient("unused"), workspace.id,
        datetime.utcnow() - timedelta(days=14),
    )
    assert outcome is None


def _register_login_and_workspace(client, email):
    client.post(
        "/auth/register",
        json={"email": email, "password": "supersecret1", "full_name": email.split("@")[0]},
    )
    login_res = client.post("/auth/login", json={"email": email, "password": "supersecret1"})
    headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}
    workspace = client.post("/workspaces/", json={"name": "Acme PMM"}, headers=headers).json()
    return headers, workspace["id"]


class _FakeScoringAndEmbeddingLLMClient:
    def complete(self, system, user, response_model):
        from app.services.llm.scoring import MaterialityResult
        return LLMCallResult(
            value=MaterialityResult(score=90, classification="pricing_move", rationale="Price hike."),
            model="fake-model", prompt_tokens=10, completion_tokens=5,
        )

    def embed(self, texts):
        from app.services.llm.client import EmbedResult
        return EmbedResult(vectors=[[0.1, 0.2, 0.3]], model="fake-embed-model", prompt_tokens=3)


def test_check_creates_embedding_when_change_is_classified(client, monkeypatch, db_session):
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

    monkeypatch.setattr(check_service, "capture_clean_snapshot", lambda url: "Plan A $10")
    client.post(check_url, headers=headers)

    monkeypatch.setattr(check_service, "get_llm_client", lambda: _FakeScoringAndEmbeddingLLMClient())
    monkeypatch.setattr(check_service, "capture_clean_snapshot", lambda url: "Plan A $15")
    client.post(check_url, headers=headers)

    embeddings = db_session.query(ChangeEmbedding).filter(
        ChangeEmbedding.workspace_id == workspace_id
    ).all()
    assert len(embeddings) == 1
    assert embeddings[0].vector == [0.1, 0.2, 0.3]
    assert embeddings[0].model == "fake-embed-model"


def test_trends_endpoint_returns_no_summary_without_llm_configured(client, monkeypatch):
    from app.routers import insights
    monkeypatch.setattr(insights, "get_llm_client", lambda: None)

    headers, workspace_id = _register_login_and_workspace(client, "dave@example.com")
    res = client.get(f"/workspaces/{workspace_id}/insights/trends", headers=headers)

    assert res.status_code == 200
    assert res.json() == {"summary": None, "based_on": 0}
