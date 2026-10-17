def test_health_and_meta(client):
    assert client.get("/api/health").json()["status"] == "ok"
    meta = client.get("/api/meta").json()
    assert meta["app_name"] == "ForteWatch"
    assert meta["features"] == {"auth": True, "uploads": True}


def test_auth_flow(client):
    creds = {"email": "Team@Example.com", "password": "secret123", "name": "Team"}
    reg = client.post("/api/auth/register", json=creds)
    assert reg.status_code == 201
    assert client.post("/api/auth/register", json=creds).status_code == 409

    login = client.post(
        "/api/auth/login", json={"email": "team@example.com", "password": "secret123"}
    )
    token = login.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["email"] == "team@example.com"

    assert client.get("/api/auth/me").status_code == 401
    bad = client.post(
        "/api/auth/login", json={"email": "team@example.com", "password": "wrong"}
    )
    assert bad.status_code == 401
