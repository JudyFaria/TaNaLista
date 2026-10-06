"""Distribuição de notificações em tempo real (Server-Sent Events).

Cada aba/celular conectado abre uma fila. Os casos de uso rodam em threads
do servidor, então a publicação usa ``call_soon_threadsafe`` para entregar
as mensagens com segurança ao loop assíncrono.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import asdict

from app.application.dto import Notification

logger = logging.getLogger(__name__)

QUEUE_SIZE = 100


class InMemoryEventBroker:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[dict]]] = defaultdict(set)
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None

    def subscribe(self, user_id: str) -> asyncio.Queue[dict]:
        """Deve ser chamado de dentro do loop assíncrono."""
        self._loop = asyncio.get_running_loop()
        queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=QUEUE_SIZE)
        with self._lock:
            self._subscribers[user_id].add(queue)
        return queue

    def unsubscribe(self, user_id: str, queue: asyncio.Queue[dict]) -> None:
        with self._lock:
            queues = self._subscribers.get(user_id)
            if queues is not None:
                queues.discard(queue)
                if not queues:
                    del self._subscribers[user_id]

    def publish(self, user_ids: Iterable[str], notification: Notification) -> None:
        if self._loop is None or self._loop.is_closed():
            return  # ninguém conectado ainda
        payload = asdict(notification)
        with self._lock:
            targets = [q for uid in set(user_ids) for q in self._subscribers.get(uid, ())]
        for queue in targets:
            self._loop.call_soon_threadsafe(self._deliver, queue, payload)

    @staticmethod
    def _deliver(queue: asyncio.Queue[dict], payload: dict) -> None:
        try:
            queue.put_nowait(payload)
        except asyncio.QueueFull:
            logger.warning("Fila de notificações cheia; mensagem descartada.")
