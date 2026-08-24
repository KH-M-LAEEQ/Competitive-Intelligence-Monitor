def _register_login(client, email):
    client.post(
        "/auth/register",
        json={"email": email, "password": "supersecret1", "full_name": email.split("@")[0]},
    )
    res = client.post("/auth/login", json={"email": email, "password": "supersecret1"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_export_my_data_includes_profile_and_created_content(client):
    headers = _register_login(client, "owner@example.com")
    workspace = client.post("/workspaces/", json={"name": "Acme"}, headers=headers).json()
    client.post(
        f"/workspaces/{workspace['id']}/competitors/", json={"name": "Rival"}, headers=headers
    )

    res = client.get("/users/me/export", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["user"]["email"] == "owner@example.com"
    assert len(data["workspace_memberships"]) == 1
    assert data["workspace_memberships"][0]["role"] == "owner"
    assert len(data["competitors_created"]) == 1
    assert data["competitors_created"][0]["name"] == "Rival"


def test_delete_account_anonymizes_and_invalidates_old_token(client):
    headers = _register_login(client, "solo@example.com")
    client.post("/workspaces/", json={"name": "Solo Co"}, headers=headers)

    res = client.delete("/users/me", headers=headers)
    assert res.status_code == 200

    # The old token's "sub" (email) no longer resolves to any user.
    me_res = client.get("/auth/me", headers=headers)
    assert me_res.status_code == 401

    # The old email is free again — proves it was actually anonymized, not just
    # blocked from future logins.
    reregister = client.post(
        "/auth/register",
        json={"email": "solo@example.com", "password": "supersecret1", "full_name": "New Person"},
    )
    assert reregister.status_code == 200


def test_delete_blocked_when_sole_owner_of_shared_workspace(client):
    owner_headers = _register_login(client, "owner@example.com")
    _register_login(client, "editor@example.com")

    workspace = client.post("/workspaces/", json={"name": "Shared Co"}, headers=owner_headers).json()
    client.post(
        f"/workspaces/{workspace['id']}/members",
        json={"email": "editor@example.com", "role": "editor"},
        headers=owner_headers,
    )

    res = client.delete("/users/me", headers=owner_headers)
    assert res.status_code == 400

    # Account must still be intact/usable after the blocked attempt.
    me_res = client.get("/auth/me", headers=owner_headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "owner@example.com"


def test_delete_allowed_when_another_owner_exists(client):
    owner_headers = _register_login(client, "owner1@example.com")
    _register_login(client, "owner2@example.com")

    workspace = client.post("/workspaces/", json={"name": "Co-owned Co"}, headers=owner_headers).json()
    client.post(
        f"/workspaces/{workspace['id']}/members",
        json={"email": "owner2@example.com", "role": "owner"},
        headers=owner_headers,
    )

    res = client.delete("/users/me", headers=owner_headers)
    assert res.status_code == 200
