def _register_login(client, email):
    client.post(
        "/auth/register",
        json={"email": email, "password": "supersecret1", "full_name": email.split("@")[0]},
    )
    res = client.post("/auth/login", json={"email": email, "password": "supersecret1"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


class _ScoringClient:
    def complete(self, system, user, response_model):
        from app.services.llm.client import LLMCallResult
        from app.services.llm.scoring import MaterialityResult
        return LLMCallResult(
            value=MaterialityResult(score=70, classification="pricing_move", rationale="x"),
            model="fake-model", prompt_tokens=10, completion_tokens=5,
        )

    def embed(self, texts):
        from app.services.llm.client import EmbedResult
        return EmbedResult(vectors=[[0.1, 0.2]], model="fake-embed", prompt_tokens=2)


def test_own_site_404_until_set(client):
    headers = _register_login(client, "owner@example.com")
    workspace = client.post("/workspaces/", json={"name": "Acme"}, headers=headers).json()

    res = client.get(f"/workspaces/{workspace['id']}/own-site/", headers=headers)
    assert res.status_code == 404


def test_set_own_site_creates_and_is_idempotent(client):
    headers = _register_login(client, "owner@example.com")
    workspace = client.post("/workspaces/", json={"name": "Acme"}, headers=headers).json()

    res = client.put(
        f"/workspaces/{workspace['id']}/own-site/",
        json={"url": "https://acme.example.com"},
        headers=headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["url"] == "https://acme.example.com/"

    # Setting again with a new URL must update in place, not create a
    # second own-site competitor.
    res2 = client.put(
        f"/workspaces/{workspace['id']}/own-site/",
        json={"url": "https://acme.example.com/pricing"},
        headers=headers,
    )
    assert res2.status_code == 200
    assert res2.json()["competitor_id"] == body["competitor_id"]
    assert res2.json()["url"] == "https://acme.example.com/pricing"


def test_own_site_excluded_from_competitors_list(client):
    headers = _register_login(client, "owner@example.com")
    workspace = client.post("/workspaces/", json={"name": "Acme"}, headers=headers).json()
    client.post(
        f"/workspaces/{workspace['id']}/competitors/", json={"name": "Rival"}, headers=headers
    )
    client.put(
        f"/workspaces/{workspace['id']}/own-site/",
        json={"url": "https://acme.example.com"},
        headers=headers,
    )

    competitors = client.get(f"/workspaces/{workspace['id']}/competitors/", headers=headers).json()
    names = [c["name"] for c in competitors]
    assert names == ["Rival"]
    assert "Your website" not in names


def test_editor_can_set_own_site_but_reviewer_cannot(client):
    owner_headers = _register_login(client, "owner@example.com")
    _register_login(client, "reviewer@example.com")
    workspace = client.post("/workspaces/", json={"name": "Acme"}, headers=owner_headers).json()
    client.post(
        f"/workspaces/{workspace['id']}/members",
        json={"email": "reviewer@example.com", "role": "reviewer"},
        headers=owner_headers,
    )
    reviewer_headers = _register_login(client, "reviewer@example.com")

    res = client.put(
        f"/workspaces/{workspace['id']}/own-site/",
        json={"url": "https://acme.example.com"},
        headers=reviewer_headers,
    )
    assert res.status_code == 403


def test_delete_own_site(client):
    headers = _register_login(client, "owner@example.com")
    workspace = client.post("/workspaces/", json={"name": "Acme"}, headers=headers).json()
    client.put(
        f"/workspaces/{workspace['id']}/own-site/",
        json={"url": "https://acme.example.com"},
        headers=headers,
    )

    res = client.delete(f"/workspaces/{workspace['id']}/own-site/", headers=headers)
    assert res.status_code == 200

    after = client.get(f"/workspaces/{workspace['id']}/own-site/", headers=headers)
    assert after.status_code == 404


def test_delete_own_site_with_change_logs_and_embeddings(client, monkeypatch):
    """Exercises the full child-before-parent deletion chain (embeddings,
    briefing links, change_logs, check_runs, snapshots, surfaces,
    competitor) with real rows present at every level — the scenario that
    broke against real Postgres (SQLite's laxer FK enforcement let an
    earlier, incorrectly-ordered version of this pass here regardless, so
    this test only confirms the row counts end up right, not that FK
    ordering is enforced; that was verified live against real Postgres).
    """
    import app.services.check_service as check_service

    headers = _register_login(client, "owner@example.com")
    workspace = client.post("/workspaces/", json={"name": "Acme"}, headers=headers).json()
    client.put(
        f"/workspaces/{workspace['id']}/own-site/",
        json={"url": "https://acme.example.com"},
        headers=headers,
    )
    own_site = client.get(f"/workspaces/{workspace['id']}/own-site/", headers=headers).json()
    check_url = (
        f"/workspaces/{workspace['id']}/competitors/{own_site['competitor_id']}"
        f"/surfaces/{own_site['surface_id']}/check"
    )

    monkeypatch.setattr(check_service, "capture_clean_snapshot", lambda url: "v1")
    client.post(check_url, headers=headers)
    monkeypatch.setattr(check_service, "get_llm_client", lambda: _ScoringClient())
    monkeypatch.setattr(check_service, "capture_clean_snapshot", lambda url: "v2")
    changed = client.post(check_url, headers=headers).json()
    assert changed["status"] == "change_detected"

    res = client.delete(f"/workspaces/{workspace['id']}/own-site/", headers=headers)
    assert res.status_code == 200

    after = client.get(f"/workspaces/{workspace['id']}/own-site/", headers=headers)
    assert after.status_code == 404


def test_delete_own_site_404_when_unset(client):
    headers = _register_login(client, "owner@example.com")
    workspace = client.post("/workspaces/", json={"name": "Acme"}, headers=headers).json()

    res = client.delete(f"/workspaces/{workspace['id']}/own-site/", headers=headers)
    assert res.status_code == 404


def test_own_site_isolated_across_workspaces(client):
    a_headers = _register_login(client, "a@example.com")
    b_headers = _register_login(client, "b@example.com")
    workspace_a = client.post("/workspaces/", json={"name": "A Co"}, headers=a_headers).json()
    workspace_b = client.post("/workspaces/", json={"name": "B Co"}, headers=b_headers).json()

    client.put(
        f"/workspaces/{workspace_a['id']}/own-site/",
        json={"url": "https://a.example.com"},
        headers=a_headers,
    )

    res = client.get(f"/workspaces/{workspace_b['id']}/own-site/", headers=b_headers)
    assert res.status_code == 404

    cross = client.get(f"/workspaces/{workspace_a['id']}/own-site/", headers=b_headers)
    assert cross.status_code == 404
