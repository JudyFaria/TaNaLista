from __future__ import annotations

from fastapi import APIRouter, Query, Response, status

from app.application.dto import GroupDetails, GroupSummary
from app.presentation.api.dependencies import ContainerDep, CurrentUser
from app.presentation.api.schemas import GroupDetailsOut, GroupIn, GroupSummaryOut

router = APIRouter(tags=["listas"])


# --- minhas listas e busca --------------------------------------------------- #
@router.get("/groups", response_model=list[GroupSummaryOut])
def list_my_groups(user: CurrentUser, container: ContainerDep) -> list[GroupSummary]:
    return container.groups.list_my_groups(user.id)


@router.post("/groups", response_model=GroupDetailsOut, status_code=status.HTTP_201_CREATED)
def create_group(body: GroupIn, user: CurrentUser, container: ContainerDep) -> GroupDetails:
    return container.groups.create_group(
        user.id, name=body.name, description=body.description, is_public=body.is_public
    )


@router.get("/groups/search", response_model=list[GroupSummaryOut])
def search_groups(
    user: CurrentUser, container: ContainerDep, q: str = Query(max_length=60)
) -> list[GroupSummary]:
    return container.groups.search(user.id, q)


# --- detalhes e gestão ------------------------------------------------------- #
@router.get("/groups/{group_id}", response_model=GroupDetailsOut)
def get_group(group_id: str, user: CurrentUser, container: ContainerDep) -> GroupDetails:
    return container.groups.get_details(user.id, group_id)


@router.put("/groups/{group_id}", response_model=GroupDetailsOut)
def update_group(
    group_id: str, body: GroupIn, user: CurrentUser, container: ContainerDep
) -> GroupDetails:
    return container.groups.update_group(
        user.id, group_id, name=body.name, description=body.description, is_public=body.is_public
    )


@router.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(group_id: str, user: CurrentUser, container: ContainerDep) -> Response:
    container.groups.delete_group(user.id, group_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/groups/{group_id}/invite-code", response_model=GroupDetailsOut)
def regenerate_invite(group_id: str, user: CurrentUser, container: ContainerDep) -> GroupDetails:
    return container.groups.regenerate_invite(user.id, group_id)


@router.post("/groups/{group_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
def leave_group(group_id: str, user: CurrentUser, container: ContainerDep) -> Response:
    container.groups.leave_group(user.id, group_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/groups/{group_id}/members/{member_id}", response_model=GroupDetailsOut)
def remove_member(
    group_id: str, member_id: str, user: CurrentUser, container: ContainerDep
) -> GroupDetails:
    return container.groups.remove_member(user.id, group_id, member_id)


# --- pedidos de entrada ------------------------------------------------------ #
@router.post(
    "/groups/{group_id}/join-requests",
    response_model=GroupSummaryOut,
    status_code=status.HTTP_201_CREATED,
)
def request_to_join(group_id: str, user: CurrentUser, container: ContainerDep) -> GroupSummary:
    return container.groups.request_to_join(user.id, group_id)


@router.delete("/groups/{group_id}/join-requests/me", status_code=status.HTTP_204_NO_CONTENT)
def cancel_request(group_id: str, user: CurrentUser, container: ContainerDep) -> Response:
    container.groups.cancel_request(user.id, group_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/groups/{group_id}/join-requests/{user_id}/approve", response_model=GroupDetailsOut)
def approve_request(
    group_id: str, user_id: str, user: CurrentUser, container: ContainerDep
) -> GroupDetails:
    return container.groups.approve_request(user.id, group_id, user_id)


@router.post("/groups/{group_id}/join-requests/{user_id}/reject", response_model=GroupDetailsOut)
def reject_request(
    group_id: str, user_id: str, user: CurrentUser, container: ContainerDep
) -> GroupDetails:
    return container.groups.reject_request(user.id, group_id, user_id)


# --- convites ---------------------------------------------------------------- #
@router.get("/invites/{code}", response_model=GroupSummaryOut)
def preview_invite(code: str, user: CurrentUser, container: ContainerDep) -> GroupSummary:
    return container.groups.preview_invite(user.id, code)


@router.post("/invites/{code}", response_model=GroupSummaryOut, status_code=status.HTTP_201_CREATED)
def accept_invite(code: str, user: CurrentUser, container: ContainerDep) -> GroupSummary:
    return container.groups.request_via_invite(user.id, code)
