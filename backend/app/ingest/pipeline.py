import hashlib
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_session_factory, init_db
from app.ingest.chunking import split_documents
from app.ingest.embedder import embed_texts
from app.ingest.loaders import guess_mime_type, iter_content_files, load_file
from app.models import Document, DocumentChunk


@dataclass
class IngestResult:
    path: str
    action: str  # ingested | skipped | failed
    detail: str = ""


def file_content_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def title_from_path(path: Path) -> str:
    return path.stem.replace("-", " ").replace("_", " ").strip().title() or path.name


def ingest_file(session: Session, path: Path, *, changed_only: bool) -> IngestResult:
    rel = path.name
    content_hash = ""
    try:
        content_hash = file_content_hash(path)
        existing = session.execute(
            select(Document).where(Document.content_hash == content_hash)
        ).scalar_one_or_none()
        if existing and existing.status == "ready" and changed_only:
            return IngestResult(rel, "skipped", "unchanged")

        lcdocs = load_file(path)
        chunks_lcdoc = split_documents(lcdocs)
        if not chunks_lcdoc:
            return IngestResult(rel, "failed", "no text extracted")

        texts = [c.page_content for c in chunks_lcdoc]
        vectors = embed_texts(texts)

        if existing:
            doc = existing
            session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc.id))
            doc.title = title_from_path(path)
            doc.filename = path.name
            doc.mime_type = guess_mime_type(path)
            doc.storage_path = rel
            doc.content_hash = content_hash
            doc.status = "processing"
            doc.error_message = None
        else:
            doc = Document(
                title=title_from_path(path),
                filename=path.name,
                mime_type=guess_mime_type(path),
                storage_path=rel,
                content_hash=content_hash,
                status="processing",
            )
            session.add(doc)
            session.flush()

        for index, (lcdoc, vector) in enumerate(zip(chunks_lcdoc, vectors, strict=True)):
            session.add(
                DocumentChunk(
                    document_id=doc.id,
                    content=lcdoc.page_content,
                    embedding=vector,
                    chunk_index=index,
                    chunk_metadata=lcdoc.metadata or None,
                )
            )

        doc.chunk_count = len(vectors)
        doc.status = "ready"
        session.commit()
        return IngestResult(rel, "ingested", f"{len(vectors)} chunks")
    except Exception as exc:
        session.rollback()
        _mark_failed(session, path, content_hash or None, str(exc))
        return IngestResult(rel, "failed", str(exc))


def _mark_failed(
    session: Session, path: Path, content_hash: str | None, message: str
) -> None:
    try:
        doc = None
        if content_hash:
            doc = session.execute(
                select(Document).where(Document.content_hash == content_hash)
            ).scalar_one_or_none()
        if doc is None:
            doc = session.execute(
                select(Document).where(Document.filename == path.name)
            ).scalar_one_or_none()
        if doc is None:
            doc = Document(
                title=title_from_path(path),
                filename=path.name,
                mime_type=guess_mime_type(path),
                storage_path=path.name,
                content_hash=content_hash or file_content_hash(path),
                status="error",
                error_message=message[:2000],
            )
            session.add(doc)
        else:
            doc.status = "error"
            doc.error_message = message[:2000]
        session.commit()
    except Exception:
        session.rollback()


def run_ingest(*, changed_only: bool = False) -> list[IngestResult]:
    settings = get_settings()
    content_dir = settings.content_dir.resolve()
    init_db()

    session_factory = get_session_factory()
    results: list[IngestResult] = []

    files = iter_content_files(content_dir)
    if not files:
        return [IngestResult(str(content_dir), "failed", "no supported files in content/")]

    with session_factory() as session:
        for path in files:
            results.append(ingest_file(session, path, changed_only=changed_only))

    return results
