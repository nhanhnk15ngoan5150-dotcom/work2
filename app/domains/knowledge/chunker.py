from app.contracts.knowledge import Chunk, Document


class KnowledgeChunker:
    def __init__(self, *, max_chars: int = 500, overlap_chars: int = 50) -> None:
        if max_chars <= 0:
            raise ValueError("Chunk max_chars must be positive")
        if not 0 <= overlap_chars < max_chars:
            raise ValueError("Chunk overlap must be between zero and max_chars")
        self._max_chars = max_chars
        self._overlap_chars = overlap_chars

    # 1. 按标题和段落构建确定性分块
    def split(self, document: Document) -> list[Chunk]:
        blocks = [
            block.strip()
            for block in document.content.replace("\r\n", "\n").split("\n\n")
            if block.strip()
        ]
        texts: list[str] = []
        buffer = ""
        for block in blocks:
            candidate = f"{buffer}\n\n{block}" if buffer else block
            if len(candidate) <= self._max_chars:
                buffer = candidate
                continue
            if buffer:
                texts.extend(self._split_long_text(buffer))
            if len(block) <= self._max_chars:
                buffer = block
            else:
                texts.extend(self._split_long_text(block))
                buffer = ""
        if buffer:
            texts.extend(self._split_long_text(buffer))

        chunks: list[Chunk] = []
        for index, text in enumerate(texts, start=1):
            metadata = document.metadata.model_copy(
                update={"chunk_id": f"{document.metadata.document_id}:{index:04d}"}
            )
            chunks.append(Chunk(content=text, metadata=metadata))
        return chunks

    def _split_long_text(self, text: str) -> list[str]:
        if len(text) <= self._max_chars:
            return [text]
        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = min(start + self._max_chars, len(text))
            chunks.append(text[start:end].strip())
            if end == len(text):
                break
            start = end - self._overlap_chars
        return chunks
