import pytest

from app.domain.errors import AuthenticationError, ConflictError, NotFoundError, ValidationError
from app.container import build_repositories


def test_register_login_and_authenticate(services):
    services.auth.register("Judy", "Judy Faria", "senha-segura")
    result = services.auth.login("judy", "senha-segura")
    assert result.user.username == "judy"
    assert services.auth.authenticate(result.access_token).display_name == "Judy Faria"


def test_login_with_wrong_password_fails(services):
    services.user("judy")
    with pytest.raises(AuthenticationError):
        services.auth.login("judy", "errada123")


@pytest.mark.parametrize("username", ["a/b", ".", "..", ""])
def test_login_with_malformed_username_fails_cleanly(services, username):
    with pytest.raises(AuthenticationError):
        services.auth.login(username, "senha-segura")


def test_duplicate_username_and_short_password(services):
    services.user("judy")
    with pytest.raises(ConflictError):
        services.auth.register("JUDY", "Outra", "senha-segura")
    with pytest.raises(ValidationError):
        services.auth.register("nova", "Nova", "curta")


def test_full_flow_invite_approval_and_item_notification(services):
    owner, mom = services.user("judy"), services.user("mae")
    group = services.groups.create_group(owner, name="Casa", description="", is_public=False)

    # Mãe usa o link de convite: vira pedido pendente e o dono é avisado.
    services.groups.request_via_invite(mom, group.invite_code)
    assert services.events.of_type("join_request")[0][0] == {owner}
    with pytest.raises(NotFoundError):
        services.items.list_items(mom, group.id)

    services.groups.approve_request(owner, group.id, mom)
    assert services.events.of_type("request_approved")[0][0] == {mom}

    # Judy adiciona café: só a mãe é notificada (quem adicionou, não).
    services.items.add_item(owner, group.id, name="Café", quantity="2", unit="pct")
    targets, notification = services.events.of_type("item_added")[0]
    assert targets == {mom}
    assert notification.body == "Judy adicionou Café (2 pct)."


def test_duplicate_pending_item_is_rejected_but_allowed_after_bought(services):
    owner = services.user("judy")
    group = services.groups.create_group(owner, name="Casa", description="", is_public=True)
    item = services.items.add_item(owner, group.id, name="Café")
    with pytest.raises(ConflictError):
        services.items.add_item(owner, group.id, name="café")

    services.items.set_bought(owner, group.id, item.id, True)
    services.items.add_item(owner, group.id, name="café")
    assert services.items.clear_bought(owner, group.id) == 1


def test_item_details_can_be_edited_by_any_member(services):
    owner = services.user("judy")
    group = services.groups.create_group(owner, name="Casa", description="", is_public=True)
    item = services.items.add_item(
        owner, group.id, name="Sabão", brand="Omo", quantity="1", unit="kg", category="limpeza"
    )
    assert (item.brand, item.unit, item.category) == ("Omo", "kg", "limpeza")

    services.items.add_item(owner, group.id, name="Leite")
    with pytest.raises(ConflictError):
        services.items.update_item(owner, group.id, item.id, name="leite")

    updated = services.items.update_item(
        owner, group.id, item.id, name="Sabão líquido", quantity="3", unit="l", category="limpeza"
    )
    assert (updated.name, updated.quantity, updated.unit, updated.brand) == ("Sabão líquido", "3", "l", "")
    saved = {i.id: i for i in services.items.list_items(owner, group.id)}
    assert saved[item.id].name == "Sabão líquido"
    assert services.events.of_type("items_changed")[-1][0] == set()  # quem editou não é avisado

    with pytest.raises(ValidationError):
        services.items.update_item(owner, group.id, item.id, name="Sabão", category="feira")


def test_search_only_returns_public_groups(services):
    owner, other = services.user("judy"), services.user("ana")
    services.groups.create_group(owner, name="Casa da praia", description="", is_public=True)
    services.groups.create_group(owner, name="Casa secreta", description="", is_public=False)

    results = services.groups.search(other, "casa")
    assert [g.name for g in results] == ["Casa da praia"]
    assert results[0].my_role is None


def test_details_hide_join_requests_from_regular_members(services):
    owner, ana, bia = services.user("judy"), services.user("ana"), services.user("bia")
    group = services.groups.create_group(owner, name="Casa", description="", is_public=True)
    services.groups.request_to_join(ana, group.id)
    services.groups.approve_request(owner, group.id, ana)
    services.groups.request_to_join(bia, group.id)

    assert len(services.groups.get_details(owner, group.id).join_requests) == 1
    assert services.groups.get_details(ana, group.id).join_requests == []


def test_delete_group_removes_items_and_notifies_members(services):
    owner, ana = services.user("judy"), services.user("ana")
    group = services.groups.create_group(owner, name="Casa", description="", is_public=True)
    services.groups.request_to_join(ana, group.id)
    services.groups.approve_request(owner, group.id, ana)
    services.items.add_item(ana, group.id, name="Leite")

    services.groups.delete_group(owner, group.id)
    assert services.groups.list_my_groups(ana) == []
    assert services.events.of_type("group_deleted")[0][0] == {ana}


def test_data_survives_a_restart(settings, services):
    owner, ana = services.user("judy"), services.user("ana")
    group = services.groups.create_group(owner, name="Casa", description="", is_public=True)
    services.groups.request_to_join(ana, group.id)
    services.items.add_item(owner, group.id, name="Café")

    # Novas instâncias dos repositórios, como se o servidor tivesse reiniciado.
    _, groups, items = build_repositories(settings)
    reloaded = groups.get(group.id)
    assert reloaded is not None and reloaded.is_owner(owner) and reloaded.has_pending_request(ana)
    assert reloaded.created_at.tzinfo is not None
    assert [i.name for i in items.list_by_group(group.id)] == ["Café"]


def test_search_treats_wildcards_literally(services):
    owner = services.user("judy")
    services.groups.create_group(owner, name="Casa", description="", is_public=True)
    assert services.groups.search(owner, "%%") == []
