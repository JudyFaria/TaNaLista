"""Canal de notificações em tempo real via Server-Sent Events (SSE).

O ``EventSource`` do navegador não envia cabeçalhos personalizados, por isso
o token vai na query string.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse

from app.presentation.api.dependencies import ContainerDep

router = APIRouter(tags=["notificações"])

HEARTBEAT_SECONDS = 20


@router.get("/events")
async def events(
    request: Request, container: ContainerDep, token: str = Query(max_length=1024)
) -> StreamingResponse:
    user = await run_in_threadpool(container.auth.authenticate, token)
    queue = container.broker.subscribe(user.id)

    async def stream() -> AsyncIterator[str]:
        try:
            yield "retry: 5000\n\n"
            while not await request.is_disconnected():
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_SECONDS)
                except TimeoutError:
                    yield ": ping\n\n"  # mantém a conexão viva em proxies
                    continue
                yield f"event: notification\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
        finally:
            container.broker.unsubscribe(user.id, queue)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
