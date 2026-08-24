def test_register_login_me_flow(client):
    register_res = client.post(
        "/auth/register",
        json={"email": "alice@example.com", "password": "supersecret1", "full_name": "Alice"},
    )
    assert register_res.status_code == 200

    duplicate_res = client.post(
        "/auth/register",
        json={"email": "alice@example.com", "password": "supersecret1", "full_name": "Alice"},
    )
    assert duplicate_res.status_code == 400

    login_res = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "supersecret1"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    me_res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "alice@example.com"


def test_me_without_token_is_unauthorized(client):
    res = client.get("/auth/me")
    assert res.status_code == 401
