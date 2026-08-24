import app.routers.category_price as category_price_router
import app.services.category_price_service as category_price_service
from app.services.llm.client import LLMCallResult


def _register_login(client, email):
    client.post(
        "/auth/register",
        json={"email": email, "password": "supersecret1", "full_name": email.split("@")[0]},
    )
    res = client.post("/auth/login", json={"email": email, "password": "supersecret1"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


class _FakePriceClient:
    def complete(self, system, user, response_model):
        from app.services.category_price_service import CategoryPriceDraft
        return LLMCallResult(
            value=CategoryPriceDraft(prices=[1500, 2500, 4000], currency="PKR"),
            model="fake-model", prompt_tokens=20, completion_tokens=10,
        )

    def embed(self, texts):
        raise NotImplementedError


def _seed_competitor_with_surface(client, headers, workspace_id, name="Rival"):
    competitor = client.post(
        f"/workspaces/{workspace_id}/competitors/", json={"name": name}, headers=headers
    ).json()
    surface = client.post(
        f"/workspaces/{workspace_id}/competitors/{competitor['id']}/surfaces/",
        json={"surface_type": "other", "url": f"https://{name.lower()}.example.com", "check_frequency": "daily"},
        headers=headers,
    ).json()
    return competitor, surface


def test_category_price_returns_stats_when_listing_found(client, monkeypatch):
    monkeypatch.setattr(category_price_router, "get_llm_client", lambda: _FakePriceClient())
    monkeypatch.setattr(
        category_price_service, "find_category_listing_url",
        lambda url, category: "https://rival.example.com/collections/mens"
    )
    monkeypatch.setattr(
        category_price_service, "capture_rendered_text",
        lambda url: "Shirt Rs. 1,500. Kurta Rs. 2,500. Sherwani Rs. 4,000."
    )

    headers = _register_login(client, "owner@example.com")
    workspace = client.post("/workspaces/", json={"name": "Acme"}, headers=headers).json()
    competitor, _ = _seed_competitor_with_surface(client, headers, workspace["id"])

    res = client.post(
        f"/workspaces/{workspace['id']}/competitors/{competitor['id']}/category-price/",
        json={"category": "Menswear"},
        headers=headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["listing_url"] == "https://rival.example.com/collections/mens"
    assert body["prices_found"] == 3
    assert body["min_price"] == 1500
    assert body["max_price"] == 4000
    assert body["avg_price"] == (1500 + 2500 + 4000) / 3
    assert body["currency"] == "PKR"


def test_category_price_returns_empty_when_no_listing_link_found(client, monkeypatch):
    monkeypatch.setattr(category_price_router, "get_llm_client", lambda: _FakePriceClient())
    monkeypatch.setattr(
        category_price_service, "find_category_listing_url", lambda url, category: None
    )

    headers = _register_login(client, "owner@example.com")
    workspace = client.post("/workspaces/", json={"name": "Acme"}, headers=headers).json()
    competitor, _ = _seed_competitor_with_surface(client, headers, workspace["id"])

    res = client.post(
        f"/workspaces/{workspace['id']}/competitors/{competitor['id']}/category-price/",
        json={"category": "Some Embedded-Only Category"},
        headers=headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["listing_url"] is None
    assert body["prices_found"] == 0
    assert body["min_price"] is None
    assert body["max_price"] is None
    assert body["avg_price"] is None


def test_category_price_returns_empty_when_page_has_no_prices(client, monkeypatch):
    class _NoPriceClient:
        def complete(self, system, user, response_model):
            from app.services.category_price_service import CategoryPriceDraft
            return LLMCallResult(
                value=CategoryPriceDraft(prices=[], currency=None),
                model="fake-model", prompt_tokens=5, completion_tokens=2,
            )

        def embed(self, texts):
            raise NotImplementedError

    monkeypatch.setattr(category_price_router, "get_llm_client", lambda: _NoPriceClient())
    monkeypatch.setattr(
        category_price_service, "find_category_listing_url",
        lambda url, category: "https://rival.example.com/collections/mens"
    )
    monkeypatch.setattr(category_price_service, "capture_rendered_text", lambda url: "Coming soon.")

    headers = _register_login(client, "owner@example.com")
    workspace = client.post("/workspaces/", json={"name": "Acme"}, headers=headers).json()
    competitor, _ = _seed_competitor_with_surface(client, headers, workspace["id"])

    res = client.post(
        f"/workspaces/{workspace['id']}/competitors/{competitor['id']}/category-price/",
        json={"category": "Menswear"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["prices_found"] == 0


def test_category_price_fails_without_llm_configured(client, monkeypatch):
    monkeypatch.setattr(category_price_router, "get_llm_client", lambda: None)

    headers = _register_login(client, "owner@example.com")
    workspace = client.post("/workspaces/", json={"name": "Acme"}, headers=headers).json()
    competitor, _ = _seed_competitor_with_surface(client, headers, workspace["id"])

    res = client.post(
        f"/workspaces/{workspace['id']}/competitors/{competitor['id']}/category-price/",
        json={"category": "Menswear"},
        headers=headers,
    )
    assert res.status_code == 400


def test_category_price_400_with_no_surface(client, monkeypatch):
    monkeypatch.setattr(category_price_router, "get_llm_client", lambda: _FakePriceClient())

    headers = _register_login(client, "owner@example.com")
    workspace = client.post("/workspaces/", json={"name": "Acme"}, headers=headers).json()
    competitor = client.post(
        f"/workspaces/{workspace['id']}/competitors/", json={"name": "Rival"}, headers=headers
    ).json()

    res = client.post(
        f"/workspaces/{workspace['id']}/competitors/{competitor['id']}/category-price/",
        json={"category": "Menswear"},
        headers=headers,
    )
    assert res.status_code == 400


def test_category_price_blocked_with_402_when_over_budget(client, monkeypatch):
    monkeypatch.setattr(category_price_router, "get_llm_client", lambda: _FakePriceClient())
    monkeypatch.setattr(
        category_price_service, "find_category_listing_url",
        lambda url, category: "https://rival.example.com/collections/mens"
    )
    monkeypatch.setattr(category_price_service, "capture_rendered_text", lambda url: "Shirt Rs. 1,500.")

    headers = _register_login(client, "owner@example.com")
    workspace = client.post("/workspaces/", json={"name": "Acme"}, headers=headers).json()
    competitor, _ = _seed_competitor_with_surface(client, headers, workspace["id"])

    client.put(
        f"/workspaces/{workspace['id']}/budget/", json={"monthly_cap_usd": 0.0}, headers=headers
    )

    res = client.post(
        f"/workspaces/{workspace['id']}/competitors/{competitor['id']}/category-price/",
        json={"category": "Menswear"},
        headers=headers,
    )
    assert res.status_code == 402


def test_reviewer_cannot_check_category_price_but_editor_can(client, monkeypatch):
    monkeypatch.setattr(category_price_router, "get_llm_client", lambda: _FakePriceClient())
    monkeypatch.setattr(
        category_price_service, "find_category_listing_url",
        lambda url, category: "https://rival.example.com/collections/mens"
    )
    monkeypatch.setattr(category_price_service, "capture_rendered_text", lambda url: "Shirt Rs. 1,500.")

    owner_headers = _register_login(client, "owner@example.com")
    _register_login(client, "reviewer@example.com")
    workspace = client.post("/workspaces/", json={"name": "Acme"}, headers=owner_headers).json()
    competitor, _ = _seed_competitor_with_surface(client, owner_headers, workspace["id"])
    client.post(
        f"/workspaces/{workspace['id']}/members",
        json={"email": "reviewer@example.com", "role": "reviewer"},
        headers=owner_headers,
    )
    reviewer_headers = _register_login(client, "reviewer@example.com")

    forbidden = client.post(
        f"/workspaces/{workspace['id']}/competitors/{competitor['id']}/category-price/",
        json={"category": "Menswear"},
        headers=reviewer_headers,
    )
    assert forbidden.status_code == 403

    allowed = client.post(
        f"/workspaces/{workspace['id']}/competitors/{competitor['id']}/category-price/",
        json={"category": "Menswear"},
        headers=owner_headers,
    )
    assert allowed.status_code == 200


def test_category_price_rejects_foreign_competitor_id(client):
    a_headers = _register_login(client, "a@example.com")
    b_headers = _register_login(client, "b@example.com")
    workspace_a = client.post("/workspaces/", json={"name": "A Co"}, headers=a_headers).json()
    workspace_b = client.post("/workspaces/", json={"name": "B Co"}, headers=b_headers).json()
    competitor_a, _ = _seed_competitor_with_surface(client, a_headers, workspace_a["id"])

    res = client.post(
        f"/workspaces/{workspace_b['id']}/competitors/{competitor_a['id']}/category-price/",
        json={"category": "Menswear"},
        headers=b_headers,
    )
    assert res.status_code == 404
