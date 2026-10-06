"""Casos de uso dos itens da lista de compras."""

from __future__ import annotations

from app.application.dto import ItemView, Notification, UserView
from app.application.ports import EventPublisher, GroupRepository, ItemRepository, UserRepository
from app.domain.entities import Group, ShoppingItem
from app.domain.errors import ConflictError, NotFoundError


class ItemService:
    def __init__(
        self,
        groups: GroupRepository,
        items: ItemRepository,
        users: UserRepository,
        events: EventPublisher,
    ) -> None:
        self._groups = groups
        self._items = items
        self._users = users
        self._events = events

    def list_items(self, actor_id: str, group_id: str) -> list[ItemView]:
        self._member_group(actor_id, group_id)
        items = self._items.list_by_group(group_id)
        # Pendentes primeiro (mais recentes no topo); comprados depois.
        items.sort(key=lambda i: i.created_at, reverse=True)
        items.sort(key=lambda i: i.is_bought)
        return self._views(items)

    def add_item(
        self, actor_id: str, group_id: str, *, name: str, quantity: str = "", note: str = ""
    ) -> ItemView:
        group = self._member_group(actor_id, group_id)
        item = ShoppingItem.create(
            group_id=group_id, name=name, quantity=quantity, note=note, added_by=actor_id
        )
        if any(not i.is_bought and i.same_name_as(item.name)
               for i in self._items.list_by_group(group_id)):
            raise ConflictError(f"“{item.name}” já está na lista.")
        self._items.save(item)

        view = self._views([item])[0]
        amount = f" ({item.quantity})" if item.quantity else ""
        self._notify_others(
            group,
            actor_id,
            Notification(
                type="item_added",
                title=group.name,
                body=f"{view.added_by.display_name} adicionou {item.name}{amount}.",
                group_id=group.id,
                data={"item_id": item.id},
            ),
        )
        return view

    def set_bought(self, actor_id: str, group_id: str, item_id: str, bought: bool) -> ItemView:
        group = self._member_group(actor_id, group_id)
        item = self._get_item(group_id, item_id)
        if bought:
            item.mark_bought(actor_id)
        else:
            item.mark_pending()
        self._items.save(item)
        self._notify_others(
            group,
            actor_id,
            Notification(type="items_changed", title=group.name, body="", group_id=group.id),
        )
        return self._views([item])[0]

    def delete_item(self, actor_id: str, group_id: str, item_id: str) -> None:
        group = self._member_group(actor_id, group_id)
        self._items.delete(self._get_item(group_id, item_id).id)
        self._notify_others(
            group,
            actor_id,
            Notification(type="items_changed", title=group.name, body="", group_id=group.id),
        )

    def clear_bought(self, actor_id: str, group_id: str) -> int:
        group = self._member_group(actor_id, group_id)
        bought = [i for i in self._items.list_by_group(group_id) if i.is_bought]
        for item in bought:
            self._items.delete(item.id)
        if bought:
            self._notify_others(
                group,
                actor_id,
                Notification(type="items_changed", title=group.name, body="", group_id=group.id),
            )
        return len(bought)

    # --- auxiliares ------------------------------------------------------ #
    def _member_group(self, actor_id: str, group_id: str) -> Group:
        group = self._groups.get(group_id)
        if group is None:
            raise NotFoundError("Lista não encontrada.")
        group.ensure_member(actor_id)
        return group

    def _get_item(self, group_id: str, item_id: str) -> ShoppingItem:
        item = self._items.get(item_id)
        if item is None or item.group_id != group_id:
            raise NotFoundError("Item não encontrado.")
        return item

    def _notify_others(self, group: Group, actor_id: str, notification: Notification) -> None:
        self._events.publish([uid for uid in group.members if uid != actor_id], notification)

    def _views(self, items: list[ShoppingItem]) -> list[ItemView]:
        user_ids = {i.added_by for i in items} | {i.bought_by for i in items if i.bought_by}
        users = self._users.get_many(user_ids)

        def view(user_id: str) -> UserView:
            user = users.get(user_id)
            return UserView.from_entity(user) if user else UserView.unknown(user_id)

        return [
            ItemView(
                id=i.id,
                name=i.name,
                quantity=i.quantity,
                note=i.note,
                added_by=view(i.added_by),
                created_at=i.created_at,
                bought_by=view(i.bought_by) if i.bought_by else None,
                bought_at=i.bought_at,
            )
            for i in items
        ]
