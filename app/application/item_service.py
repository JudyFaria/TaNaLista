"""Casos de uso dos itens da lista de compras."""

from __future__ import annotations

from app.application.dto import ItemView, Notification, UserView
from app.application.ports import (
    EventPublisher,
    GroupRepository,
    ItemImageRepository,
    ItemRepository,
    UserRepository,
)
from app.domain.entities import Group, ItemImage, ShoppingItem
from app.domain.errors import ConflictError, NotFoundError


class ItemService:
    def __init__(
        self,
        groups: GroupRepository,
        items: ItemRepository,
        users: UserRepository,
        events: EventPublisher,
        images: ItemImageRepository,
    ) -> None:
        self._groups = groups
        self._items = items
        self._users = users
        self._events = events
        self._images = images

    def list_items(self, actor_id: str, group_id: str) -> list[ItemView]:
        self._member_group(actor_id, group_id)
        items = self._items.list_by_group(group_id)
        # Pendentes primeiro (mais recentes no topo); comprados depois.
        items.sort(key=lambda i: i.created_at, reverse=True)
        items.sort(key=lambda i: i.is_bought)
        return self._views(items)

    def add_item(self, actor_id: str, group_id: str, **details) -> ItemView:
        """``details``: name, quantity, unit, brand, category e note (ver ``ShoppingItem``)."""
        group = self._member_group(actor_id, group_id)
        item = ShoppingItem.create(group_id=group_id, added_by=actor_id, **details)
        self._ensure_not_duplicate(item)
        self._items.save(item)

        view = self._views([item])[0]
        amount = f" ({item.quantity} {item.unit})" if item.quantity else ""
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

    def update_item(self, actor_id: str, group_id: str, item_id: str, **details) -> ItemView:
        group = self._member_group(actor_id, group_id)
        item = self._get_item(group_id, item_id)
        item.update_details(**details)
        self._ensure_not_duplicate(item)
        self._items.save(item)
        self._notify_others(
            group,
            actor_id,
            Notification(type="items_changed", title=group.name, body="", group_id=group.id),
        )
        return self._views([item])[0]

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

    def set_image(self, actor_id: str, group_id: str, item_id: str, data: bytes) -> ItemView:
        """Anexa (ou troca) a foto do item. ``data`` é a imagem já reduzida pelo celular."""
        group = self._member_group(actor_id, group_id)
        item = self._get_item(group_id, item_id)
        image = ItemImage.create(item_id=item.id, group_id=group_id, data=data)
        self._images.save(image)
        item.attach_image(image)
        self._items.save(item)
        self._notify_changed(group, actor_id)
        return self._views([item])[0]

    def get_image(self, actor_id: str, group_id: str, item_id: str) -> ItemImage:
        self._member_group(actor_id, group_id)
        item = self._get_item(group_id, item_id)
        image = self._images.get(item.id) if item.has_image else None
        if image is None:
            raise NotFoundError("Este item não tem foto.")
        return image

    def remove_image(self, actor_id: str, group_id: str, item_id: str) -> ItemView:
        group = self._member_group(actor_id, group_id)
        item = self._get_item(group_id, item_id)
        if item.has_image:
            item.detach_image()
            self._items.save(item)
            self._images.delete(item.id)
            self._notify_changed(group, actor_id)
        return self._views([item])[0]

    def delete_item(self, actor_id: str, group_id: str, item_id: str) -> None:
        group = self._member_group(actor_id, group_id)
        item = self._get_item(group_id, item_id)
        self._items.delete(item.id)
        if item.has_image:
            self._images.delete(item.id)
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
            if item.has_image:
                self._images.delete(item.id)
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

    def _ensure_not_duplicate(self, item: ShoppingItem) -> None:
        if item.is_bought:
            return
        if any(other.id != item.id and not other.is_bought and other.same_name_as(item.name)
               for other in self._items.list_by_group(item.group_id)):
            raise ConflictError(f"“{item.name}” já está na lista.")

    def _get_item(self, group_id: str, item_id: str) -> ShoppingItem:
        item = self._items.get(item_id)
        if item is None or item.group_id != group_id:
            raise NotFoundError("Item não encontrado.")
        return item

    def _notify_changed(self, group: Group, actor_id: str) -> None:
        self._notify_others(
            group,
            actor_id,
            Notification(type="items_changed", title=group.name, body="", group_id=group.id),
        )

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
                unit=i.unit,
                brand=i.brand,
                category=i.category,
                note=i.note,
                added_by=view(i.added_by),
                created_at=i.created_at,
                bought_by=view(i.bought_by) if i.bought_by else None,
                bought_at=i.bought_at,
                has_image=i.has_image,
                image_updated_at=i.image_updated_at,
            )
            for i in items
        ]
