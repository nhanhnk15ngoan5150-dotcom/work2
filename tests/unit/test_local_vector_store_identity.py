from pathlib import Path

from app.contracts.evidence import EvidenceDomain
from app.contracts.knowledge import Chunk, KnowledgeMetadata
from app.infrastructure.knowledge.local_vector_store import LocalVectorStore

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEST_INDEX_PATH = PROJECT_ROOT / "data" / ".vector_collision_test.json"


def _chunk(
    tenant_id: str,
    content: str,
    *,
    knowledge_base_id: str = "operations",
    version: str = "1.0",
) -> Chunk:
    return Chunk(
        content=content,
        metadata=KnowledgeMetadata(
            tenant_id=tenant_id,
            domains=[EvidenceDomain.KNOWLEDGE_OPERATION],
            knowledge_base_id=knowledge_base_id,
            document_id="membership-rules",
            chunk_id="membership-rules:0001",
            source=f"{tenant_id}/{knowledge_base_id}/membership-rules.md",
            version=version,
        ),
    )


def _contents(store: LocalVectorStore, tenant_id: str) -> set[str]:
    return {
        result.chunk.content
        for result in store.search(
            [1.0, 0.0],
            tenant_id=tenant_id,
            domains=[EvidenceDomain.KNOWLEDGE_OPERATION],
            limit=10,
        )
    }


def test_composite_identity_survives_multi_tenant_persistence_reload() -> None:
    TEST_INDEX_PATH.unlink(missing_ok=True)
    try:
        store = LocalVectorStore(TEST_INDEX_PATH)
        store.upsert(
            [
                _chunk("tenant_a", "tenant A version 1"),
                _chunk("tenant_b", "tenant B version 1"),
                _chunk(
                    "tenant_a",
                    "tenant A other knowledge base",
                    knowledge_base_id="policy",
                ),
                _chunk("tenant_a", "tenant A version 2", version="2.0"),
            ],
            [[1.0, 0.0]] * 4,
        )

        assert _contents(store, "tenant_a") == {
            "tenant A version 1",
            "tenant A other knowledge base",
            "tenant A version 2",
        }
        assert _contents(store, "tenant_b") == {"tenant B version 1"}

        reloaded = LocalVectorStore(TEST_INDEX_PATH)

        assert _contents(reloaded, "tenant_a") == {
            "tenant A version 1",
            "tenant A other knowledge base",
            "tenant A version 2",
        }
        assert _contents(reloaded, "tenant_b") == {"tenant B version 1"}
    finally:
        TEST_INDEX_PATH.unlink(missing_ok=True)
