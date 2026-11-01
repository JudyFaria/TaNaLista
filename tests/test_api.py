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

    edited = client.put(
        f"/api/groups/{gid}/items/{item['id']}",
        json={"name": "Café", "brand": "Pilão", "quantity": "500", "unit": "g", "category": "mantimentos"},
        headers=judy,
    ).json()
    assert (edited["brand"], edited["unit"], edited["category"]) == ("Pilão", "g", "mantimentos")
    bad = client.put(f"/api/groups/{gid}/items/{item['id']}", json={"name": "Café", "unit": "tonelada"}, headers=judy)
    assert bad.status_code == 422

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


def test_item_image_flow(client):
    judy, mae, intruso = register(client, "judy"), register(client, "mae"), register(client, "intruso")
    gid = client.post("/api/groups", json={"name": "Casa", "is_public": True}, headers=judy).json()["id"]
    client.post(f"/api/groups/{gid}/join-requests", headers=mae)
    mae_id = client.get("/api/auth/me", headers=mae).json()["id"]
    client.post(f"/api/groups/{gid}/join-requests/{mae_id}/approve", headers=judy)

    item = client.post(f"/api/groups/{gid}/items", json={"name": "Café"}, headers=judy).json()
    assert item["has_image"] is False
    url = f"/api/groups/{gid}/items/{item['id']}/image"
    assert client.get(url, headers=judy).status_code == 404  # sem foto

    photo = b"\xff\xd8\xff\xe0" + b"jpeg-bytes" * 10
    saved = client.put(url, content=photo, headers={**judy, "Content-Type": "image/jpeg"})
    assert saved.status_code == 200 and saved.json()["has_image"] is True

    # Outro usuário da lista vê o item com foto e baixa a imagem.
    listed = client.get(f"/api/groups/{gid}/items", headers=mae).json()
    assert listed[0]["has_image"] is True
    downloaded = client.get(url, headers=mae)
    assert downloaded.status_code == 200
    assert downloaded.headers["content-type"] == "image/jpeg"
    assert downloaded.content == photo

    # Quem não é da lista não descobre nem a lista, nem a foto.
    assert client.get(url, headers=intruso).status_code == 404
    assert client.put(url, content=photo, headers=intruso).status_code == 404
    assert client.get(url).status_code == 401

    # Conteúdo que não é imagem, ou grande demais, é recusado.
    assert client.put(url, content=b"texto", headers=judy).status_code == 422
    assert client.put(url, content=photo + b"\x00" * 500_000, headers=judy).status_code == 422

    removed = client.delete(url, headers=judy)
    assert removed.status_code == 200 and removed.json()["has_image"] is False
    assert client.get(url, headers=mae).status_code == 404
