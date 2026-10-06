"""Casos de uso de grupos (listas): criar, buscar, convidar e moderar entrada."""

from __future__ import annotations

from app.application.dto import (
    GroupDetails,
    GroupSummary,
    JoinRequestView,
    MemberView,
    Notification,
    UserView,
)
from app.application.ports import EventPublisher, GroupRepository, ItemRepository, UserRepository
from app.domain.entities import Group
from app.domain.errors import NotFoundError, ValidationError

SEARCH_MIN_LENGTH = 2
SEARCH_LIMIT = 20


class GroupService:
    def __init__(
        self,
        groups: GroupRepository,
        users: UserRepository,
        items: ItemRepository,
        events: EventPublisher,
    ) -> None:
        self._groups = groups
        self._users = users
        self._items = items
        self._events = events

    # --- consultas ------------------------------------------------------- #
    def list_my_groups(self, actor_id: str) -> list[GroupSummary]:
        groups = sorted(self._groups.list_for_user(actor_id), key=lambda g: g.name.casefold())
        return [self._summary(g, actor_id, include_items=True) for g in groups]

    def search(self, actor_id: str, query: str) -> list[GroupSummary]:
        query = " ".join((query or "").split())
        if len(query) < SEARCH_MIN_LENGTH:
            raise ValidationError(f"Digite pelo menos {SEARCH_MIN_LENGTH} letras para buscar.")
        return [self._summary(g, actor_id) for g in self._groups.search_public(query, SEARCH_LIMIT)]

    def get_details(self, actor_id: str, group_id: str) -> GroupDetails:
        group = self._get_group(group_id)
        group.ensure_member(actor_id)
        return self._details(group, actor_id)

    def preview_invite(self, actor_id: str, invite_code: str) -> GroupSummary:
        return self._summary(self._get_by_invite(invite_code), actor_id)

    # --- criação e edição ------------------------------------------------ #
    def create_group(
        self, actor_id: str, *, name: str, description: str, is_public: bool
    ) -> GroupDetails:
        group = Group.create(
            name=name, description=description, is_public=is_public, owner_id=actor_id
        )
        self._groups.save(group)
        return self._details(group, actor_id)

    def update_group(
        self, actor_id: str, group_id: str, *, name: str, description: str, is_public: bool
    ) -> GroupDetails:
        group = self._get_group(group_id)
        group.update_details(actor_id, name=name, description=description, is_public=is_public)
        self._groups.save(group)
        return self._details(group, actor_id)

    def regenerate_invite(self, actor_id: str, group_id: str) -> GroupDetails:
        group = self._get_group(group_id)
        group.regenerate_invite_code(actor_id)
        self._groups.save(group)
        return self._details(group, actor_id)

    def delete_group(self, actor_id: str, group_id: str) -> None:
        group = self._get_group(group_id)
        group.ensure_owner(actor_id)
        other_members = [uid for uid in group.members if uid != actor_id]
        self._items.delete_by_group(group.id)
        self._groups.delete(group.id)
        self._events.publish(
            other_members,
            Notification(
                type="group_deleted",
                title="Lista excluída",
                body=f"A lista “{group.name}” foi excluída pelo dono.",
                group_id=group.id,
            ),
        )

    # --- entrada na lista ------------------------------------------------ #
    def request_to_join(self, actor_id: str, group_id: str) -> GroupSummary:
        return self._request(self._get_group(group_id), actor_id, via_invite=False)

    def request_via_invite(self, actor_id: str, invite_code: str) -> GroupSummary:
        return self._request(self._get_by_invite(invite_code), actor_id, via_invite=True)

    def cancel_request(self, actor_id: str, group_id: str) -> None:
        group = self._get_group(group_id)
        group.cancel_request(actor_id)
        self._groups.save(group)

    def approve_request(self, actor_id: str, group_id: str, user_id: str) -> GroupDetails:
        group = self._get_group(group_id)
        group.approve_request(actor_id, user_id)
        self._groups.save(group)

        self._events.publish(
            [user_id],
            Notification(
                type="request_approved",
                title="Pedido aprovado",
                body=f"Você agora participa da lista “{group.name}”.",
                group_id=group.id,
            ),
        )
        new_member = self._users.get(user_id)
        if new_member:
            self._events.publish(
                [uid for uid in group.members if uid not in (actor_id, user_id)],
                Notification(
                    type="member_joined",
                    title=group.name,
                    body=f"{new_member.display_name} entrou na lista.",
                    group_id=group.id,
                ),
            )
        return self._details(group, actor_id)

    def reject_request(self, actor_id: str, group_id: str, user_id: str) -> GroupDetails:
        group = self._get_group(group_id)
        group.reject_request(actor_id, user_id)
        self._groups.save(group)
        return self._details(group, actor_id)

    # --- saída ----------------------------------------------------------- #
    def remove_member(self, actor_id: str, group_id: str, user_id: str) -> GroupDetails:
        group = self._get_group(group_id)
        group.remove_member(actor_id, user_id)
        self._groups.save(group)
        self._events.publish(
            [user_id],
            Notification(
                type="member_removed",
                title="Removido da lista",
                body=f"Você foi removido da lista “{group.name}”.",
                group_id=group.id,
            ),
        )
        return self._details(group, actor_id)

    def leave_group(self, actor_id: str, group_id: str) -> None:
        group = self._get_group(group_id)
        group.leave(actor_id)
        self._groups.save(group)

    # --- auxiliares ------------------------------------------------------ #
    def _request(self, group: Group, actor_id: str, *, via_invite: bool) -> GroupSummary:
        group.request_to_join(actor_id, via_invite=via_invite)
        self._groups.save(group)

        requester = self._users.get(actor_id)
        name = requester.display_name if requester else "Alguém"
        self._events.publish(
            [group.owner_id],
            Notification(
                type="join_request",
                title="Pedido para entrar",
                body=f"{name} quer entrar na lista “{group.name}”.",
                group_id=group.id,
            ),
        )
        return self._summary(group, actor_id)

    def _get_group(self, group_id: str) -> Group:
        group = self._groups.get(group_id)
        if group is None:
            raise NotFoundError("Lista não encontrada.")
        return group

    def _get_by_invite(self, invite_code: str) -> Group:
        group = self._groups.get_by_invite_code((invite_code or "").strip())
        if group is None:
            raise NotFoundError("Convite inválido ou expirado.")
        return group

    def _summary(self, group: Group, actor_id: str, *, include_items: bool = False) -> GroupSummary:
        pending_items = None
        if include_items and group.is_member(actor_id):
            pending_items = sum(1 for i in self._items.list_by_group(group.id) if not i.is_bought)
        return GroupSummary(
            id=group.id,
            name=group.name,
            description=group.description,
            is_public=group.is_public,
            member_count=len(group.members),
            my_role=group.role_of(actor_id),
            has_pending_request=group.has_pending_request(actor_id),
            pending_items=pending_items,
            pending_requests=len(group.join_requests) if group.is_owner(actor_id) else 0,
        )

    def _details(self, group: Group, actor_id: str) -> GroupDetails:
        is_owner = group.is_owner(actor_id)
        user_ids = set(group.members) | (set(group.join_requests) if is_owner else set())
        users = self._users.get_many(user_ids)

        def view(user_id: str) -> UserView:
            user = users.get(user_id)
            return UserView.from_entity(user) if user else UserView.unknown(user_id)

        members = sorted(
            (MemberView(user=view(m.user_id), role=m.role, joined_at=m.joined_at)
             for m in group.members.values()),
            key=lambda m: (m.role != "owner", m.user.display_name.casefold()),
        )
        requests = (
            sorted(
                (JoinRequestView(user=view(r.user_id), via_invite=r.via_invite,
                                 requested_at=r.requested_at)
                 for r in group.join_requests.values()),
                key=lambda r: r.requested_at,
            )
            if is_owner
            else []
        )
        role = group.role_of(actor_id)
        assert role is not None  # garantido por ensure_member nos chamadores
        return GroupDetails(
            id=group.id,
            name=group.name,
            description=group.description,
            is_public=group.is_public,
            invite_code=group.invite_code,
            my_role=role,
            members=members,
            join_requests=requests,
        )
