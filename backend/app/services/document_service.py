import tempfile
import os
import uuid
import re
from fastapi import UploadFile
from langchain_community.document_loaders import PyPDFLoader, WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.vector_store import get_chroma_collection, get_embedding_model

class DocumentService:
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )

    async def process_pdf_content(self, content: bytes, filename: str, org_id: int):
        """Saves uploaded PDF bytes temporarily, extracts text, and ingests with org_id."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name

        try:
            loader = PyPDFLoader(tmp_path)
            docs = loader.load()
            if not docs or all(not d.page_content.strip() for d in docs):
                raise ValueError("No readable text could be extracted from this PDF.")
            self._ingest_documents(docs, source=filename, org_id=org_id)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    async def process_pdf(self, file: UploadFile, org_id: int):
        """Wrapper for direct UploadFile processing."""
        content = await file.read()
        await self.process_pdf_content(content, file.filename, org_id)

    def process_url(self, url: str, org_id: int):
        """Scrapes a URL, extracts text, and ingests it."""
        url_clean = url.strip()
        if not re.match(r"^https?://[a-zA-Z0-9\-.]+", url_clean):
            raise ValueError("Invalid URL scheme. Must start with http:// or https://")

        loader = WebBaseLoader(url_clean)
        docs = loader.load()
        if not docs:
            raise ValueError(f"Could not retrieve readable content from {url_clean}")
        self._ingest_documents(docs, source=url_clean, org_id=org_id)

    def _ingest_documents(self, docs, source: str, org_id: int):
        """Chunks documents, generates embeddings, and saves to ChromaDB with org_id metadata."""
        chunks = self.text_splitter.split_documents(docs)
        if not chunks:
            return

        texts = [chunk.page_content for chunk in chunks]
        metadatas = [{"source": source, "org_id": org_id} for _ in chunks]
        ids = [str(uuid.uuid4()) for _ in chunks]

        embedding_model = get_embedding_model()
        collection = get_chroma_collection()

        embeddings = embedding_model.embed_documents(texts)
        collection.add(
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )