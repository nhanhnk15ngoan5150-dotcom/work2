from __future__ import annotations

import json
from collections.abc import Sequence
from math import isfinite, sqrt
from pathlib import Path
from typing import Any

from app.contracts.evidence import EvidenceDomain
from app.contracts.knowledge import Chunk, Citation, RetrievalResult

RecordIdentity = tuple[str, str, str, str, str]


class LocalVectorStore:
    """Small local vector store for Batch 3 demo knowledge."""

    def __init__(self, persistence_path: Path | None = None) -> None:
        self._persistence_path = persistence_path
        self._records: dict[RecordIdentity, tuple[Chunk, list[float]]] = {}
        if persistence_path is not None and persistence_path.exists():
            self._load()

    # 1. 保存知识分块与向量
    def upsert(
        self,
        chunks: Sequence[Chunk],
        vectors: Sequence[Sequence[float]],
    ) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("Chunk and vector counts must match")
        for chunk, raw_vector in zip(chunks, vectors, strict=True):
            vector = _validate_vector(raw_vector)
            record_id = _record_identity(chunk)
            self._records[record_id] = (chunk, vector)
        if self._persistence_path is not None:
            self._persist()

    # 2. 使用 Tenant / Domain Guard 执行余弦检索
    def search(
        self,
        vector: Sequence[float],
        *,
        tenant_id: str,
        domains: Sequence[EvidenceDomain],
        limit: int,
    ) -> list[RetrievalResult]:
        if limit <= 0:
            raise ValueError("Vector search limit must be positive")
        query_vector = _validate_vector(vector)
        requested_domains = set(domains)
        scored: list[RetrievalResult] = []
        for chunk, stored_vector in self._records.values():
            metadata = chunk.metadata
            if metadata.tenant_id != tenant_id:
                continue
            if requested_domains.isdisjoint(metadata.domains):
                continue
            score = _cosine_similarity(query_vector, stored_vector)
            scored.append(
                RetrievalResult(
                    chunk=chunk,
                    score=score,
                    citation=Citation(
                        document_id=metadata.document_id,
                        chunk_id=metadata.chunk_id or "",
                        source=metadata.source,
                        version=metadata.version,
                        excerpt=chunk.content,
                    ),
                )
            )
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:limit]

    def _persist(self) -> None:
        assert self._persistence_path is not None
        self._persistence_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [
            {
                "record_id": list(record_id),
                "chunk": chunk.model_dump(mode="json"),
                "vector": vector,
            }
            for record_id, (chunk, vector) in self._records.items()
        ]
        self._persistence_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _load(self) -> None:
        assert self._persistence_path is not None
        try:
            payload: Any = json.loads(
                self._persistence_path.read_text(encoding="utf-8")
            )
            if not isinstance(payload, list):
                raise ValueError("Vector index must be a list")
            for item in payload:
                if not isinstance(item, dict):
                    raise ValueError("Vector index item must be an object")
                chunk = Chunk.model_validate(item["chunk"])
                vector = _validate_vector(item["vector"])
                record_id = _record_identity(chunk)
                persisted_id = item.get("record_id")
                if persisted_id != list(record_id):
                    raise ValueError("Vector index record identity is invalid")
                self._records[record_id] = (chunk, vector)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("Local vector index is invalid") from exc


def _record_identity(chunk: Chunk) -> RecordIdentity:
    metadata = chunk.metadata
    if metadata.chunk_id is None:
        raise ValueError("Vector store chunk_id is required")
    return (
        metadata.tenant_id,
        metadata.knowledge_base_id,
        metadata.document_id,
        metadata.version,
        metadata.chunk_id,
    )


def _validate_vector(vector: Sequence[float]) -> list[float]:
    if not vector:
        raise ValueError("Vector cannot be empty")
    values = [float(value) for value in vector]
    if any(not isfinite(value) for value in values):
        raise ValueError("Vector values must be finite")
    return values


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise ValueError("Vector dimensions must match")
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    score = sum(a * b for a, b in zip(left, right, strict=True)) / (
        left_norm * right_norm
    )
    return max(-1.0, min(1.0, score))
