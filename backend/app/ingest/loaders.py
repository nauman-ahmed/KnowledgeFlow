import mimetypes
from pathlib import Path

from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader, TextLoader
from langchain_core.documents import Document as LCDocument

SUPPORTED_SUFFIXES = {".txt", ".md", ".pdf", ".docx"}


_MIME_BY_SUFFIX = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def guess_mime_type(path: Path) -> str:
    if path.suffix.lower() in _MIME_BY_SUFFIX:
        return _MIME_BY_SUFFIX[path.suffix.lower()]
    mime, _ = mimetypes.guess_type(path.name)
    return mime or "application/octet-stream"


def load_file(path: Path) -> list[LCDocument]:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(f"Unsupported file type: {suffix}")

    if suffix in {".txt", ".md"}:
        loader = TextLoader(str(path), encoding="utf-8")
    elif suffix == ".pdf":
        loader = PyPDFLoader(str(path))
    elif suffix == ".docx":
        loader = Docx2txtLoader(str(path))
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

    docs = loader.load()
    for doc in docs:
        doc.metadata.setdefault("source", path.name)
        doc.metadata.setdefault("filename", path.name)
    return docs


def iter_content_files(content_dir: Path) -> list[Path]:
    if not content_dir.is_dir():
        return []
    files = [
        p
        for p in sorted(content_dir.iterdir())
        if p.is_file() and not p.name.startswith(".") and p.suffix.lower() in SUPPORTED_SUFFIXES
    ]
    return files
