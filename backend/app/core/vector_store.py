import os
import chromadb
from langchain_huggingface import HuggingFaceEmbeddings

# Define where ChromaDB will store its SQLite and Parquet files locally
CHROMA_DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../chroma_data"))
os.makedirs(CHROMA_DB_DIR, exist_ok=True)

_chroma_client = None
_collection = None
_embedding_model = None

def get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
    return _chroma_client

def get_chroma_collection():
    global _collection
    if _collection is None:
        client = get_chroma_client()
        _collection = client.get_or_create_collection(
            name="marketing_assets",
            metadata={"hnsw:space": "cosine"}
        )
    return _collection

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        # Downloads model weights once and caches locally
        _embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    return _embedding_model