import app.services.check_service as check_service


def _register_login_and_workspace(client, email):
    client.post(
        "/auth/register",
        json={"email": email, "password": "supersecret1", "full_name": email.split("@")[0]},
    )
    login_res = client.post("/auth/login", json={"email": email, "password": "supersecret1"})
    headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

    workspace = client.post("/workspaces/", json={"name": "Acme PMM"}, headers=headers).json()
    return headers, workspace["id"]


def _add_competitor_and_surface(client, headers, workspace_id, url="https://rival.example.com/pricing"):
    competitor = client.post(
        f"/workspaces/{workspace_id}/competitors/",
        json={"name": "Rival"},
        headers=headers,
    ).json()

    surface = client.post(
        f"/workspaces/{workspace_id}/competitors/{competitor['id']}/surfaces/",
        json={"surface_type": "pricing", "url": url, "check_frequency": "daily"},
        headers=headers,
    ).json()

    return competitor, surface


def test_first_check_captures_baseline(client, monkeypatch):
    headers, workspace_id = _register_login_and_workspace(client, "alice@example.com")
    competitor, surface = _add_competitor_and_surface(client, headers, workspace_id)

    monkeypatch.setattr(check_service, "capture_clean_snapshot", lambda url: "Plan A $10\nPlan B $20")

    check_res = client.post(
        f"/workspaces/{workspace_id}/competitors/{competitor['id']}/surfaces/{surface['id']}/check",
        headers=headers,
    )
    assert check_res.status_code == 200
    assert check_res.json()["status"] == "baseline_captured"


def test_second_check_with_same_content_reports_no_change(client, monkeypatch):
    headers, workspace_id = _register_login_and_workspace(client, "alice@example.com")
    competitor, surface = _add_competitor_and_surface(client, headers, workspace_id)

    monkeypatch.setattr(check_service, "capture_clean_snapshot", lambda url: "Plan A $10\nPlan B $20")
    check_url = f"/workspaces/{workspace_id}/competitors/{competitor['id']}/surfaces/{surface['id']}/check"

    client.post(check_url, headers=headers)
    second_res = client.post(check_url, headers=headers)

    assert second_res.json()["status"] == "no_change"


def test_third_check_with_changed_content_creates_change_log(client, monkeypatch):
    headers, workspace_id = _register_login_and_workspace(client, "alice@example.com")
    competitor, surface = _add_competitor_and_surface(client, headers, workspace_id)
    check_url = f"/workspaces/{workspace_id}/competitors/{competitor['id']}/surfaces/{surface['id']}/check"

    monkeypatch.setattr(check_service, "capture_clean_snapshot", lambda url: "Plan A $10\nPlan B $20")
    client.post(check_url, headers=headers)

    monkeypatch.setattr(check_service, "capture_clean_snapshot", lambda url: "Plan A $15\nPlan B $20")
    changed_res = client.post(check_url, headers=headers)

    assert changed_res.json()["status"] == "change_detected"

    logs_res = client.get(f"/workspaces/{workspace_id}/change-logs/", headers=headers)
    assert logs_res.status_code == 200
    logs = logs_res.json()
    assert len(logs) == 1
    assert logs[0]["surface_id"] == surface["id"]
    assert "Plan A" in logs[0]["diff"]
