import pytest

from app.domain.entities import Group, Role, ShoppingItem, User
from app.domain.errors import ConflictError, NotFoundError, PermissionDeniedError, ValidationError


def make_group(is_public: bool = True) -> Group:
    return Group.create(name="  Casa  ", description="", is_public=is_public, owner_id="dono")


def test_group_creator_is_owner_and_name_is_trimmed():
    group = make_group()
    assert group.name == "Casa"
    assert group.owner_id == "dono"
    assert group.role_of("dono") is Role.OWNER


def test_join_request_must_be_approved_by_owner():
    group = make_group()
    group.request_to_join("ana", via_invite=False)
    assert not group.is_member("ana")

    with pytest.raises(NotFoundError):  # quem não é membro nem enxerga a lista
        group.approve_request("intruso", "ana")

    group.approve_request("dono", "ana")
    assert group.role_of("ana") is Role.MEMBER
    assert not group.has_pending_request("ana")


def test_member_cannot_approve_requests():
    group = make_group()
    group.request_to_join("ana", via_invite=True)
    group.approve_request("dono", "ana")
    group.request_to_join("bia", via_invite=True)

    with pytest.raises(PermissionDeniedError):
        group.approve_request("ana", "bia")


def test_duplicate_request_and_member_request_are_rejected():
    group = make_group()
    group.request_to_join("ana", via_invite=False)
    with pytest.raises(ConflictError):
        group.request_to_join("ana", via_invite=False)
    with pytest.raises(ConflictError):
        group.request_to_join("dono", via_invite=False)


def test_private_group_only_accepts_requests_via_invite():
    group = make_group(is_public=False)
    with pytest.raises(NotFoundError):
        group.request_to_join("ana", via_invite=False)
    group.request_to_join("ana", via_invite=True)
    assert group.has_pending_request("ana")


def test_owner_cannot_leave_and_regenerating_invite_changes_code():
    group = make_group()
    with pytest.raises(ConflictError):
        group.leave("dono")
    old = group.invite_code
    assert group.regenerate_invite_code("dono") != old


@pytest.mark.parametrize("username", ["ab", "com espaço", "x" * 31, "acento-é"])
def test_invalid_usernames(username):
    with pytest.raises(ValidationError):
        User.create(username, "Nome", "hash")


def test_item_without_new_fields_loads_with_defaults():
    from app.infrastructure.persistence import mappers

    old = mappers.item_to_dict(ShoppingItem.create(group_id="g", name="Café", added_by="ana"))
    for key in ("brand", "unit", "category"):
        del old[key]
    item = mappers.item_from_dict(old)
    assert (item.brand, item.unit, item.category) == ("", "un", "outros")


def test_item_bought_cycle():
    item = ShoppingItem.create(group_id="g", name=" Café ", added_by="ana")
    assert item.name == "Café" and not item.is_bought
    item.mark_bought("bia")
    assert item.is_bought and item.bought_by == "bia"
    item.mark_pending()
    assert not item.is_bought
    assert item.same_name_as("  café ")
