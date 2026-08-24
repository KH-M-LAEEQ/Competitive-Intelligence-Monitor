from PIL import Image, ImageDraw

import app.services.check_service as check_service
from app.services.visual_diff import compare


def _make_image(path, shape):
    """phash is a structural hash, not a color hash — a solid-color image
    has no internal structure to differentiate, so these draw distinct
    shapes rather than just filling with different colors.
    """
    img = Image.new("RGB", (200, 200), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    if shape == "square":
        draw.rectangle([10, 10, 90, 90], fill=(0, 0, 0))
    else:
        draw.ellipse([110, 110, 190, 190], fill=(0, 0, 0))
    img.save(path)


def test_compare_identical_images_scores_zero(tmp_path):
    a = tmp_path / "a.png"
    b = tmp_path / "b.png"
    _make_image(a, "square")
    _make_image(b, "square")

    assert compare(str(a), str(b)) == 0.0


def test_compare_returns_a_plain_python_float(tmp_path):
    """Regression test: imagehash's `-` operator returns a numpy scalar, not
    a plain float. psycopg2 has no adapter for numpy types and fails to bind
    it against a real Postgres column (SQLite silently accepts it, which is
    exactly how this slipped past the test suite the first time — it only
    surfaced against the real Postgres DB). `compare()` must always return
    a genuine `float` so it can be written to ChangeLog.visual_diff_score.
    """
    a = tmp_path / "a.png"
    b = tmp_path / "b.png"
    _make_image(a, "square")
    _make_image(b, "circle")

    score = compare(str(a), str(b))
    assert type(score) is float


def test_compare_different_images_scores_above_zero(tmp_path):
    a = tmp_path / "a.png"
    b = tmp_path / "b.png"
    _make_image(a, "square")
    _make_image(b, "circle")

    score = compare(str(a), str(b))
    assert 0.0 < score <= 1.0


def _register_login_and_workspace(client, email):
    client.post(
        "/auth/register",
        json={"email": email, "password": "supersecret1", "full_name": email.split("@")[0]},
    )
    login_res = client.post("/auth/login", json={"email": email, "password": "supersecret1"})
    headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}
    workspace = client.post("/workspaces/", json={"name": "Acme PMM"}, headers=headers).json()
    return headers, workspace["id"]


def test_check_computes_visual_diff_score_for_capture_visual_surface(
    client, monkeypatch, tmp_path
):
    headers, workspace_id = _register_login_and_workspace(client, "alice@example.com")
    competitor = client.post(
        f"/workspaces/{workspace_id}/competitors/", json={"name": "Rival"}, headers=headers
    ).json()
    surface = client.post(
        f"/workspaces/{workspace_id}/competitors/{competitor['id']}/surfaces/",
        json={
            "surface_type": "pricing",
            "url": "https://rival.example.com",
            "check_frequency": "daily",
            "capture_visual": True,
        },
        headers=headers,
    ).json()
    check_url = (
        f"/workspaces/{workspace_id}/competitors/{competitor['id']}"
        f"/surfaces/{surface['id']}/check"
    )

    screenshots = iter([str(tmp_path / "shot1.png"), str(tmp_path / "shot2.png")])
    _make_image(tmp_path / "shot1.png", "square")
    _make_image(tmp_path / "shot2.png", "circle")

    monkeypatch.setattr(check_service, "capture_screenshot", lambda url, sid: next(screenshots))
    monkeypatch.setattr(check_service, "capture_clean_snapshot", lambda url: "Plan A $10")
    client.post(check_url, headers=headers)

    monkeypatch.setattr(check_service, "capture_clean_snapshot", lambda url: "Plan A $15")
    changed_res = client.post(check_url, headers=headers)
    assert changed_res.json()["status"] == "change_detected"

    logs = client.get(f"/workspaces/{workspace_id}/change-logs/", headers=headers).json()
    assert len(logs) == 1
    assert logs[0]["visual_diff_score"] is not None
    assert logs[0]["visual_diff_score"] > 0


def test_check_skips_visual_diff_when_capture_visual_is_false(client, monkeypatch):
    headers, workspace_id = _register_login_and_workspace(client, "bob@example.com")
    competitor = client.post(
        f"/workspaces/{workspace_id}/competitors/", json={"name": "Rival"}, headers=headers
    ).json()
    surface = client.post(
        f"/workspaces/{workspace_id}/competitors/{competitor['id']}/surfaces/",
        json={
            "surface_type": "pricing",
            "url": "https://rival.example.com",
            "check_frequency": "daily",
            "capture_visual": False,
        },
        headers=headers,
    ).json()
    check_url = (
        f"/workspaces/{workspace_id}/competitors/{competitor['id']}"
        f"/surfaces/{surface['id']}/check"
    )

    def _fail_if_called(*args, **kwargs):
        raise AssertionError("capture_screenshot should not be called when capture_visual=False")

    monkeypatch.setattr(check_service, "capture_screenshot", _fail_if_called)
    monkeypatch.setattr(check_service, "capture_clean_snapshot", lambda url: "Plan A $10")
    client.post(check_url, headers=headers)
    monkeypatch.setattr(check_service, "capture_clean_snapshot", lambda url: "Plan A $15")
    changed_res = client.post(check_url, headers=headers)

    assert changed_res.json()["status"] == "change_detected"
