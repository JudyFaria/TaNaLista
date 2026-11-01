from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.application.dto import ItemView
from app.presentation.api.dependencies import ContainerDep, CurrentUser
from app.presentation.api.schemas import ClearedOut, ItemIn, ItemOut, ItemStatusIn

router = APIRouter(prefix="/groups/{group_id}/items", tags=["itens"])


@router.get("", response_model=list[ItemOut])
def list_items(group_id: str, user: CurrentUser, container: ContainerDep) -> list[ItemView]:
    return container.items.list_items(user.id, group_id)


@router.post("", response_model=ItemOut, status_code=status.HTTP_201_CREATED)
def add_item(group_id: str, body: ItemIn, user: CurrentUser, container: ContainerDep) -> ItemView:
    return container.items.add_item(user.id, group_id, **body.model_dump())


@router.delete("/bought", response_model=ClearedOut)
def clear_bought(group_id: str, user: CurrentUser, container: ContainerDep) -> ClearedOut:
    return ClearedOut(removed=container.items.clear_bought(user.id, group_id))


@router.put("/{item_id}", response_model=ItemOut)
def update_item(
    group_id: str, item_id: str, body: ItemIn, user: CurrentUser, container: ContainerDep
) -> ItemView:
    return container.items.update_item(user.id, group_id, item_id, **body.model_dump())


@router.patch("/{item_id}", response_model=ItemOut)
def set_status(
    group_id: str, item_id: str, body: ItemStatusIn, user: CurrentUser, container: ContainerDep
) -> ItemView:
    return container.items.set_bought(user.id, group_id, item_id, body.bought)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(group_id: str, item_id: str, user: CurrentUser, container: ContainerDep) -> Response:
    container.items.delete_item(user.id, group_id, item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
