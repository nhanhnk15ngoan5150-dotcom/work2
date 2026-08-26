from app.contracts.knowledge import Document
from app.contracts.providers import VectorStoreProvider
from app.domains.knowledge.chunker import KnowledgeChunker
from app.domains.knowledge.embedding_service import EmbeddingService


class KnowledgeIndexer:
    def __init__(
        self,
        chunker: KnowledgeChunker,
        embedding_service: EmbeddingService,
        vector_store: VectorStoreProvider,
    ) -> None:
        self._chunker = chunker
        self._embedding_service = embedding_service
        self._vector_store = vector_store

    # 1. 构建知识分块和向量索引
    async def index(self, documents: list[Document]) -> int:
        chunks = [
            chunk
            for document in documents
            for chunk in self._chunker.split(document)
        ]
        if not chunks:
            return 0
        vectors = await self._embedding_service.embed(
            [chunk.content for chunk in chunks]
        )
        self._vector_store.upsert(chunks, vectors)
        return len(chunks)
