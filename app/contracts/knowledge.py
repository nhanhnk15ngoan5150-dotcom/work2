from pydantic import BaseModel, Field, model_validator

from app.contracts.evidence import EvidenceDomain


class KnowledgeMetadata(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=128)
    domains: list[EvidenceDomain] = Field(min_length=1)
    knowledge_base_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    chunk_id: str | None = None
    source: str = Field(min_length=1)
    version: str = Field(min_length=1)


class Document(BaseModel):
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    metadata: KnowledgeMetadata


class Chunk(BaseModel):
    content: str = Field(min_length=1)
    metadata: KnowledgeMetadata

    @model_validator(mode="after")
    def require_chunk_id(self) -> "Chunk":
        if self.metadata.chunk_id is None:
            raise ValueError("Chunk metadata requires chunk_id")
        return self


class Citation(BaseModel):
    document_id: str = Field(min_length=1)
    chunk_id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    version: str = Field(min_length=1)
    excerpt: str = Field(min_length=1)


class RetrievalResult(BaseModel):
    chunk: Chunk
    score: float = Field(ge=-1.0, le=1.0)
    citation: Citation
