def register(client, username: str) -> dict[str, str]:
    response = client.post(
        "/api/auth/register",
        json={"username": username, "display_name": username.title(), "password": "senha-segura"},
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_requires_authentication(client):
    response = client.get("/api/groups")
    assert response.status_code == 401
    assert response.json()["detail"] == "Faça login para continuar."


def test_end_to_end_flow(client):
    judy, mae = register(client, "judy"), register(client, "mae")

    group = client.post("/api/groups", json={"name": "Casa", "is_public": True}, headers=judy).json()
    gid, code = group["id"], group["invite_code"]

    # Busca + pedido de entrada
    found = client.get("/api/groups/search", params={"q": "cas"}, headers=mae).json()
    assert [g["id"] for g in found] == [gid]
    assert client.post(f"/api/invites/{code}", headers=mae).json()["has_pending_request"] is True

    # Ainda não é membro
    assert client.get(f"/api/groups/{gid}/items", headers=mae).status_code == 404

    # Dono aprova
    mae_id = client.get("/api/auth/me", headers=mae).json()["id"]
    details = client.post(f"/api/groups/{gid}/join-requests/{mae_id}/approve", headers=judy).json()
    assert {m["user"]["username"] for m in details["members"]} == {"judy", "mae"}

    # Itens
    item = client.post(f"/api/groups/{gid}/items", json={"name": "Café"}, headers=mae).json()
    assert item["added_by"]["username"] == "mae"
    assert client.post(f"/api/groups/{gid}/items", json={"name": "café"}, headers=judy).status_code == 409

    bought = client.patch(f"/api/groups/{gid}/items/{item['id']}", json={"bought": True}, headers=judy)
    assert bought.json()["bought_by"]["username"] == "judy"

    mine = client.get("/api/groups", headers=mae).json()
    assert mine[0]["pending_items"] == 0


def test_member_cannot_approve_or_delete(client):
    judy, ana = register(client, "judy"), register(client, "ana")
    gid = client.post("/api/groups", json={"name": "Casa"}, headers=judy).json()["id"]
    client.post(f"/api/groups/{gid}/join-requests", headers=ana)
    ana_id = client.get("/api/auth/me", headers=ana).json()["id"]
    client.post(f"/api/groups/{gid}/join-requests/{ana_id}/approve", headers=judy)

    assert client.delete(f"/api/groups/{gid}", headers=ana).status_code == 403
    assert client.post(f"/api/groups/{gid}/invite-code", headers=ana).status_code == 403


def test_frontend_is_served_with_security_headers(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Lista de Compras" in response.text
    assert "default-src 'self'" in response.headers["content-security-policy"]
