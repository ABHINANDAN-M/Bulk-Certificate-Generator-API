"""Bonus features: JWT auth and rate limiting."""


def test_protected_routes_require_token(make_env, payload):
    env = make_env(auth_enabled=True)
    assert env.client.post("/api/v1/jobs", json=payload).status_code == 401
    assert env.client.get("/health").status_code == 200       # public
    assert env.client.get("/verify/x").status_code == 200     # public


def test_login_and_use_token(make_env, payload):
    env = make_env(auth_enabled=True)
    bad = env.client.post("/api/v1/auth/token", json={"username": "admin", "password": "x"})
    assert bad.status_code == 401

    token = env.client.post(
        "/api/v1/auth/token", json={"username": "admin", "password": "pw"}
    ).json()["access_token"]
    r = env.client.post("/api/v1/jobs", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 202

    forged = env.client.post("/api/v1/jobs", json=payload, headers={"Authorization": "Bearer abc"})
    assert forged.status_code == 401


def test_rate_limit_returns_429(make_env):
    env = make_env(rate_limit_per_minute=3)
    codes = [env.client.get("/verify/x").status_code for _ in range(5)]
    assert codes == [200, 200, 200, 429, 429]
    assert env.client.get("/health").status_code == 200  # health is exempt
