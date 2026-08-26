from pathlib import Path

from app.contracts.knowledge import Document, KnowledgeMetadata

SUPPORTED_SUFFIXES = {".txt", ".md"}


class TextDocumentParser:
    # 1. 解析 txt / md 知识文档
    def parse(self, path: Path, metadata: KnowledgeMetadata) -> Document:
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            raise ValueError(f"Unsupported document type: {path.suffix}")
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            raise ValueError("Knowledge document is empty")
        title = self._extract_title(path, content)
        return Document(title=title, content=content, metadata=metadata)

    @staticmethod
    def _extract_title(path: Path, content: str) -> str:
        first_line = content.splitlines()[0].strip()
        if first_line.startswith("#"):
            heading = first_line.lstrip("#").strip()
            if heading:
                return heading
        return path.stem
