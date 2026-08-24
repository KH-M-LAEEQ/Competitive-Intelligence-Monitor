def _register_login(client, email):
    client.post(
        "/auth/register",
        json={"email": email, "password": "supersecret1", "full_name": email.split("@")[0]},
    )
    res = client.post("/auth/login", json={"email": email, "password": "supersecret1"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _seed_workspace_and_competitor(client, owner_headers):
    workspace = client.post("/workspaces/", json={"name": "Acme"}, headers=owner_headers).json()
    competitor = client.post(
        f"/workspaces/{workspace['id']}/competitors/", json={"name": "Rival"}, headers=owner_headers
    ).json()
    return workspace, competitor


def test_get_profile_404_before_created(client):
    owner_headers = _register_login(client, "owner@example.com")
    workspace, competitor = _seed_workspace_and_competitor(client, owner_headers)

    res = client.get(
        f"/workspaces/{workspace['id']}/competitors/{competitor['id']}/profile/", headers=owner_headers
    )
    assert res.status_code == 404


def test_create_and_update_profile(client):
    owner_headers = _register_login(client, "owner@example.com")
    workspace, competitor = _seed_workspace_and_competitor(client, owner_headers)

    create_res = client.put(
        f"/workspaces/{workspace['id']}/competitors/{competitor['id']}/profile/",
        json={
            "industry": "SaaS",
            "hq_location": "San Francisco, CA",
            "employee_range": "51-200",
            "funding_stage": "Series B",
            "key_people": [{"name": "Jane Doe", "title": "CEO"}],
            "notes_markdown": "Aggressive on pricing.",
        },
        headers=owner_headers,
    )
    assert create_res.status_code == 200
    profile = create_res.json()
    assert profile["industry"] == "SaaS"
    assert profile["key_people"] == [{"name": "Jane Doe", "title": "CEO"}]

    update_res = client.put(
        f"/workspaces/{workspace['id']}/competitors/{competitor['id']}/profile/",
        json={"industry": "Fintech", "notes_markdown": "Pivoted."},
        headers=owner_headers,
    )
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["id"] == profile["id"]
    assert updated["industry"] == "Fintech"
    assert updated["hq_location"] is None

    get_res = client.get(
        f"/workspaces/{workspace['id']}/competitors/{competitor['id']}/profile/", headers=owner_headers
    )
    assert get_res.json()["industry"] == "Fintech"


def test_reviewer_cannot_edit_profile(client):
    owner_headers = _register_login(client, "owner@example.com")
    reviewer_headers = _register_login(client, "reviewer@example.com")
    workspace, competitor = _seed_workspace_and_competitor(client, owner_headers)

    client.post(
        f"/workspaces/{workspace['id']}/members",
        json={"email": "reviewer@example.com", "role": "reviewer"},
        headers=owner_headers,
    )

    res = client.put(
        f"/workspaces/{workspace['id']}/competitors/{competitor['id']}/profile/",
        json={"industry": "SaaS"},
        headers=reviewer_headers,
    )
    assert res.status_code == 403
