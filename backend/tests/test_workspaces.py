def _register_and_login(client, email):
    client.post(
        "/auth/register",
        json={"email": email, "password": "supersecret1", "full_name": email.split("@")[0]},
    )
    res = client.post("/auth/login", json={"email": email, "password": "supersecret1"})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_new_user_can_create_and_list_workspace(client):
    headers = _register_and_login(client, "alice@example.com")

    create_res = client.post("/workspaces/", json={"name": "Acme PMM"}, headers=headers)
    assert create_res.status_code == 200
    workspace = create_res.json()
    assert workspace["slug"] == "acme-pmm"

    list_res = client.get("/workspaces/", headers=headers)
    assert list_res.status_code == 200
    workspaces = list_res.json()
    assert len(workspaces) == 1
    assert workspaces[0]["role"] == "owner"


def test_cross_tenant_competitor_access_is_blocked(client):
    alice_headers = _register_and_login(client, "alice@example.com")
    bob_headers = _register_and_login(client, "bob@example.com")

    alice_workspace = client.post(
        "/workspaces/", json={"name": "Alice Co"}, headers=alice_headers
    ).json()

    add_res = client.post(
        f"/workspaces/{alice_workspace['id']}/competitors/",
        json={"name": "Rival"},
        headers=alice_headers,
    )
    assert add_res.status_code == 200

    # Bob has no membership in Alice's workspace at all.
    bob_list_res = client.get(
        f"/workspaces/{alice_workspace['id']}/competitors/", headers=bob_headers
    )
    assert bob_list_res.status_code == 404

    alice_list_res = client.get(
        f"/workspaces/{alice_workspace['id']}/competitors/", headers=alice_headers
    )
    assert alice_list_res.status_code == 200
    assert len(alice_list_res.json()) == 1


def test_editor_cannot_change_roles(client):
    owner_headers = _register_and_login(client, "owner@example.com")
    editor_headers = _register_and_login(client, "editor@example.com")

    workspace = client.post(
        "/workspaces/", json={"name": "Shared Workspace"}, headers=owner_headers
    ).json()

    invite_res = client.post(
        f"/workspaces/{workspace['id']}/members",
        json={"email": "editor@example.com", "role": "editor"},
        headers=owner_headers,
    )
    assert invite_res.status_code == 200
    member_id = invite_res.json()["id"]

    forbidden_res = client.patch(
        f"/workspaces/{workspace['id']}/members/{member_id}",
        json={"role": "owner"},
        headers=editor_headers,
    )
    assert forbidden_res.status_code == 403
