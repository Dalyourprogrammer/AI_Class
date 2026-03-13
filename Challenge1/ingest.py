"""
ingest.py — One-time script to chunk The Art of War and load into ChromaDB.
Run once: python ingest.py
"""

import os
import chromadb
from sentence_transformers import SentenceTransformer

ART_OF_WAR_PATH = os.path.join(os.path.dirname(__file__), "The Art of War.txt")
CHROMA_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")
COLLECTION_NAME = "art_of_war"
CHUNK_SIZE = 200      # tokens (approximate — using words as proxy)
CHUNK_OVERLAP = 20


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def main():
    print("Loading text...")
    with open(ART_OF_WAR_PATH, "r", encoding="utf-8") as f:
        text = f.read()

    chunks = chunk_text(text)
    print(f"Created {len(chunks)} chunks")

    print("Loading embedding model...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    print("Embedding chunks...")
    embeddings = model.encode(chunks, show_progress_bar=True).tolist()

    print("Loading into ChromaDB...")
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    # Drop and recreate for a clean ingest
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

    ids = [f"chunk_{i}" for i in range(len(chunks))]
    collection.add(documents=chunks, embeddings=embeddings, ids=ids)

    print(f"Done. {collection.count()} chunks stored in ChromaDB at {CHROMA_PATH}")


if __name__ == "__main__":
    main()
