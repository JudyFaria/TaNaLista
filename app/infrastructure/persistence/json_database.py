"""Banco de dados local em um único arquivo JSON.

- Mantém os dados em memória e grava no disco a cada transação.
- A gravação é atômica (arquivo temporário + ``os.replace``), então uma queda
  no meio da escrita não corrompe o arquivo.
- Um ``RLock`` serializa o acesso entre as threads do servidor.

Usado no desenvolvimento local; em produção os dados ficam no Firestore
(mesmas portas, veja ``firestore_repositories``).
"""

from __future__ import annotations

import copy
import json
import os
import tempfile
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

Collection = dict[str, dict[str, Any]]


class JsonDatabase:
    COLLECTIONS = ("users", "groups", "items", "item_imgs")

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.RLock()
        self._data: dict[str, Collection] = self._load()

    @contextmanager
    def read(self) -> Iterator[dict[str, Collection]]:
        with self._lock:
            yield self._data

    @contextmanager
    def transaction(self) -> Iterator[dict[str, Collection]]:
        """Aplica as mudanças e grava; em caso de erro, desfaz tudo."""
        with self._lock:
            snapshot = copy.deepcopy(self._data)
            try:
                yield self._data
                self._flush()
            except BaseException:
                self._data = snapshot
                raise

    def _load(self) -> dict[str, Collection]:
        data: dict[str, Collection] = {}
        if self._path.exists():
            data = json.loads(self._path.read_text(encoding="utf-8") or "{}")
        for name in self.COLLECTIONS:
            data.setdefault(name, {})
        return data

    def _flush(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=self._path.parent, prefix=".db-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as tmp:
                json.dump(self._data, tmp, ensure_ascii=False, indent=2)
                tmp.flush()
                os.fsync(tmp.fileno())
            os.replace(tmp_name, self._path)
        except BaseException:
            Path(tmp_name).unlink(missing_ok=True)
            raise
