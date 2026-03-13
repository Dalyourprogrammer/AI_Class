"""
rag.py — RAG query interface for The Art of War ChromaDB collection.
"""

import os
import chromadb
from sentence_transformers import SentenceTransformer

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")
COLLECTION_NAME = "art_of_war"

_model = None
_collection = None


def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        _collection = client.get_collection(COLLECTION_NAME)
    return _collection


def query_rag(query_text: str, n_results: int = 3) -> list[str]:
    """Return top-n relevant text chunks from The Art of War."""
    model = _get_model()
    collection = _get_collection()
    embedding = model.encode([query_text]).tolist()
    results = collection.query(query_embeddings=embedding, n_results=n_results)
    return results["documents"][0]
