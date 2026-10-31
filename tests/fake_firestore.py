"""Firestore falso, em memória, com só o que os repositórios usam.

Permite rodar os testes do adaptador Firestore sem rede nem emulador.
"""

from __future__ import annotations

import copy
from typing import Any

from google.api_core.exceptions import AlreadyExists

Store = dict[str, dict[str, dict[str, Any]]]


class FakeFirestore:
    def __init__(self) -> None:
        self.store: Store = {}

    def collection(self, name: str) -> FakeCollection:
        return FakeCollection(self.store.setdefault(name, {}))

    def batch(self) -> FakeBatch:
        return FakeBatch()

    def get_all(self, refs):
        return [ref.get() for ref in refs]


class FakeSnapshot:
    def __init__(self, ref: FakeDocument, data: dict[str, Any] | None) -> None:
        self.reference = ref
        self.id = ref.id
        self.exists = data is not None
        self._data = copy.deepcopy(data)

    def to_dict(self) -> dict[str, Any] | None:
        return copy.deepcopy(self._data)


class FakeDocument:
    def __init__(self, docs: dict[str, dict[str, Any]], doc_id: str) -> None:
        if not doc_id or "/" in doc_id or doc_id in (".", ".."):
            raise ValueError(f"ID de documento inválido: {doc_id!r}")
        self._docs = docs
        self.id = doc_id

    def get(self) -> FakeSnapshot:
        return FakeSnapshot(self, self._docs.get(self.id))

    def set(self, data: dict[str, Any]) -> None:
        self._docs[self.id] = copy.deepcopy(data)

    def create(self, data: dict[str, Any]) -> None:
        if self.id in self._docs:
            raise AlreadyExists(f"Documento {self.id} já existe.")
        self.set(data)

    def delete(self) -> None:
        self._docs.pop(self.id, None)


class FakeQuery:
    def __init__(self, docs: dict[str, dict[str, Any]], filters=(), limit: int | None = None) -> None:
        self._docs = docs
        self._filters = tuple(filters)
        self._limit = limit

    def where(self, *, filter) -> FakeQuery:
        return FakeQuery(self._docs, (*self._filters, filter), self._limit)

    def limit(self, count: int) -> FakeQuery:
        return FakeQuery(self._docs, self._filters, count)

    def stream(self):
        matches = [
            FakeSnapshot(FakeDocument(self._docs, doc_id), data)
            for doc_id, data in list(self._docs.items())
            if all(_matches(data, f) for f in self._filters)
        ]
        return iter(matches[: self._limit] if self._limit is not None else matches)


class FakeCollection(FakeQuery):
    def document(self, doc_id: str) -> FakeDocument:
        return FakeDocument(self._docs, doc_id)


class FakeBatch:
    """Aplica tudo ou nada, como a gravação em lote do Firestore."""

    def __init__(self) -> None:
        self._ops: list[tuple[str, FakeDocument, Any]] = []

    def set(self, ref: FakeDocument, data: dict[str, Any]) -> None:
        self._ops.append(("set", ref, data))

    def create(self, ref: FakeDocument, data: dict[str, Any]) -> None:
        self._ops.append(("create", ref, data))

    def delete(self, ref: FakeDocument) -> None:
        self._ops.append(("delete", ref, None))

    def commit(self) -> None:
        for op, ref, _ in self._ops:
            if op == "create" and ref.get().exists:
                raise AlreadyExists(f"Documento {ref.id} já existe.")
        for op, ref, data in self._ops:
            if op == "delete":
                ref.delete()
            else:
                ref.set(data)


def _matches(data: dict[str, Any], f) -> bool:
    value = data.get(f.field_path)
    if f.op_string == "==":
        return value == f.value
    if f.op_string == "array_contains":
        return isinstance(value, list) and f.value in value
    raise NotImplementedError(f.op_string)
