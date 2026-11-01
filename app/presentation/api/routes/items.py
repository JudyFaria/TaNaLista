from __future__ import annotations

from fastapi import APIRouter, Request, Response, status
from starlette.concurrency import run_in_threadpool

from app.application.dto import ItemView
from app.domain.entities import MAX_IMAGE_BYTES
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


async def _read_image_body(request: Request) -> bytes:
    """Lê o corpo (a imagem em bytes) parando logo depois do limite, sem encher a memória."""
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        chunks.append(chunk)
        size += len(chunk)
        if size > MAX_IMAGE_BYTES:
            break  # grande demais: o domínio recusa com a mensagem certa
    return b"".join(chunks)


# A foto vai como corpo binário (sem multipart), já reduzida pelo celular.
@router.put("/{item_id}/image", response_model=ItemOut)
async def put_image(
    group_id: str, item_id: str, request: Request, user: CurrentUser, container: ContainerDep
) -> ItemView:
    data = await _read_image_body(request)
    return await run_in_threadpool(container.items.set_image, user.id, group_id, item_id, data)


@router.get("/{item_id}/image", response_class=Response)
def get_image(group_id: str, item_id: str, user: CurrentUser, container: ContainerDep) -> Response:
    image = container.items.get_image(user.id, group_id, item_id)
    # A foto só é acessível a membros da lista, então nada de cache compartilhado.
    return Response(
        content=image.data,
        media_type=image.content_type,
        headers={"Cache-Control": "private, no-cache"},
    )


@router.delete("/{item_id}/image", response_model=ItemOut)
def delete_image(group_id: str, item_id: str, user: CurrentUser, container: ContainerDep) -> ItemView:
    return container.items.remove_image(user.id, group_id, item_id)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(group_id: str, item_id: str, user: CurrentUser, container: ContainerDep) -> Response:
    container.items.delete_item(user.id, group_id, item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
