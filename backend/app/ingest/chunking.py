from langchain_core.documents import Document as LCDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import get_settings


def split_documents(documents: list[LCDocument]) -> list[LCDocument]:
    settings = get_settings()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.ingest_chunk_size,
        chunk_overlap=settings.ingest_chunk_overlap,
        length_function=len,
    )
    return splitter.split_documents(documents)
