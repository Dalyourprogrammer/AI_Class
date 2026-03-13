"""
rag_mvp.py — Minimal viable example. Run this first to validate ChromaDB + embeddings.
Usage: python rag_mvp.py
"""

import chromadb
from sentence_transformers import SentenceTransformer

SAMPLE_CHUNKS = [
    "Supreme excellence consists in breaking the enemy's resistance without fighting.",
    "The rush of water, to the point of tossing rocks about — this is Shi.",
    "If you know the enemy and know yourself, you need not fear the result of a hundred battles.",
    "There is no instance of a country having benefited from prolonged warfare.",
    "The general who advances without coveting fame and retreats without fearing disgrace protects his country.",
]

QUERY = "victory without fighting"

model = SentenceTransformer("all-MiniLM-L6-v2")
client = chromadb.Client()
collection = client.create_collection("mvp_test", metadata={"hnsw:space": "cosine"})

embeddings = model.encode(SAMPLE_CHUNKS).tolist()
collection.add(documents=SAMPLE_CHUNKS, embeddings=embeddings, ids=[f"c{i}" for i in range(len(SAMPLE_CHUNKS))])

query_vec = model.encode([QUERY]).tolist()
results = collection.query(query_embeddings=query_vec, n_results=2)

print(f"\nQuery: '{QUERY}'\n")
for i, doc in enumerate(results["documents"][0]):
    print(f"Result {i+1}: {doc}\n")
