from pathlib import Path

from langchain_core.documents import Document as LCDocument

from app.ingest.chunking import split_documents
from app.ingest.loaders import guess_mime_type, iter_content_files
from app.ingest.pipeline import file_content_hash, title_from_path


def test_title_from_path() -> None:
    assert title_from_path(Path("compound-interest.txt")) == "Compound Interest"


def test_guess_mime_type() -> None:
    assert guess_mime_type(Path("doc.md")) == "text/markdown"


def test_split_documents_produces_chunks() -> None:
    docs = [LCDocument(page_content="word " * 500, metadata={"source": "t.md"})]
    chunks = split_documents(docs)
    assert len(chunks) >= 1
    assert all(c.page_content.strip() for c in chunks)


def test_content_dir_lists_seed_files() -> None:
    from app.core.config import get_settings

    get_settings.cache_clear()
    files = iter_content_files(get_settings().content_dir)
    assert len(files) >= 5


def test_file_content_hash_stable(tmp_path: Path) -> None:
    p = tmp_path / "a.txt"
    p.write_text("hello", encoding="utf-8")
    assert file_content_hash(p) == file_content_hash(p)
