from datetime import date

import app.services.traffic_service as traffic_service
from app.core.config import settings


def _register_login(client, email):
    client.post(
        "/auth/register",
        json={"email": email, "password": "supersecret1", "full_name": email.split("@")[0]},
    )
    res = client.post("/auth/login", json={"email": email, "password": "supersecret1"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _seed_competitor(client, headers):
    workspace = client.post("/workspaces/", json={"name": "Acme"}, headers=headers).json()
    competitor = client.post(
        f"/workspaces/{workspace['id']}/competitors/", json={"name": "Rival"}, headers=headers
    ).json()
    return workspace, competitor


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


def test_refresh_fails_without_website_domain(client, monkeypatch):
    monkeypatch.setattr(settings, "similarweb_api_key", "fake-key")
    headers = _register_login(client, "owner@example.com")
    workspace, competitor = _seed_competitor(client, headers)

    res = client.post(
        f"/workspaces/{workspace['id']}/competitors/{competitor['id']}/traffic/refresh",
        headers=headers,
    )
    assert res.status_code == 400


def test_refresh_fails_when_similarweb_not_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "similarweb_api_key", None)
    headers = _register_login(client, "owner@example.com")
    workspace, competitor = _seed_competitor(client, headers)

    client.put(
        f"/workspaces/{workspace['id']}/competitors/{competitor['id']}/profile/",
        json={"website_domain": "rival.com"},
        headers=headers,
    )

    res = client.post(
        f"/workspaces/{workspace['id']}/competitors/{competitor['id']}/traffic/refresh",
        headers=headers,
    )
    assert res.status_code == 502
    assert "not configured" in res.json()["detail"]


def test_refresh_stores_and_upserts_snapshots(client, monkeypatch):
    monkeypatch.setattr(settings, "similarweb_api_key", "fake-key")
    headers = _register_login(client, "owner@example.com")
    workspace, competitor = _seed_competitor(client, headers)

    client.put(
        f"/workspaces/{workspace['id']}/competitors/{competitor['id']}/profile/",
        json={"website_domain": "rival.com"},
        headers=headers,
    )

    fake_payload = {
        "visits": [
            {"date": "2026-05-01", "visits": 1000000.0},
            {"date": "2026-06-01", "visits": 1200000.0},
        ]
    }
    monkeypatch.setattr(
        traffic_service.requests, "get", lambda *a, **k: _FakeResponse(fake_payload)
    )

    res = client.post(
        f"/workspaces/{workspace['id']}/competitors/{competitor['id']}/traffic/refresh",
        headers=headers,
    )
    assert res.status_code == 200
    snapshots = res.json()
    assert len(snapshots) == 2
    assert snapshots[0]["month"] == "2026-05-01"
    assert snapshots[0]["visits"] == 1000000
    assert snapshots[1]["visits"] == 1200000

    list_res = client.get(
        f"/workspaces/{workspace['id']}/competitors/{competitor['id']}/traffic/", headers=headers
    ).json()
    assert len(list_res) == 2

    # Refresh again with updated numbers for the same months — must upsert,
    # not create duplicate rows.
    updated_payload = {
        "visits": [
            {"date": "2026-05-01", "visits": 1100000.0},
            {"date": "2026-06-01", "visits": 1200000.0},
        ]
    }
    monkeypatch.setattr(
        traffic_service.requests, "get", lambda *a, **k: _FakeResponse(updated_payload)
    )
    client.post(
        f"/workspaces/{workspace['id']}/competitors/{competitor['id']}/traffic/refresh",
        headers=headers,
    )
    list_res_2 = client.get(
        f"/workspaces/{workspace['id']}/competitors/{competitor['id']}/traffic/", headers=headers
    ).json()
    assert len(list_res_2) == 2
    assert list_res_2[0]["visits"] == 1100000


def test_traffic_list_rejects_foreign_competitor_id(client, monkeypatch):
    monkeypatch.setattr(settings, "similarweb_api_key", "fake-key")
    a_headers = _register_login(client, "a@example.com")
    b_headers = _register_login(client, "b@example.com")
    _, a_competitor = _seed_competitor(client, a_headers)
    b_workspace, _ = _seed_competitor(client, b_headers)

    res = client.get(
        f"/workspaces/{b_workspace['id']}/competitors/{a_competitor['id']}/traffic/",
        headers=b_headers,
    )
    assert res.status_code == 404


def test_editor_can_refresh_but_reviewer_cannot(client, monkeypatch):
    monkeypatch.setattr(settings, "similarweb_api_key", "fake-key")
    owner_headers = _register_login(client, "owner@example.com")
    _register_login(client, "reviewer@example.com")
    workspace, competitor = _seed_competitor(client, owner_headers)
    client.post(
        f"/workspaces/{workspace['id']}/members",
        json={"email": "reviewer@example.com", "role": "reviewer"},
        headers=owner_headers,
    )
    reviewer_headers = _register_login(client, "reviewer@example.com")

    client.put(
        f"/workspaces/{workspace['id']}/competitors/{competitor['id']}/profile/",
        json={"website_domain": "rival.com"},
        headers=owner_headers,
    )

    res = client.post(
        f"/workspaces/{workspace['id']}/competitors/{competitor['id']}/traffic/refresh",
        headers=reviewer_headers,
    )
    assert res.status_code == 403
