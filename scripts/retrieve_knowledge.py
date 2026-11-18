
import json
from pathlib import Path

import numpy as np


BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_FILE = BASE_DIR / "data" / "tomato_knowledge.json"

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


class NumpyIndex:
    """Exact cosine search for the small knowledge base, without FAISS."""
    def __init__(self, embeddings):
        self.embeddings = embeddings
        self.ntotal = len(embeddings)

    def search(self, query, k):
        scores = query @ self.embeddings.T
        indices = np.argsort(-scores, axis=1, kind="stable")[:, :k]
        return np.take_along_axis(scores, indices, axis=1), indices


def load_knowledge():
    with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def build_index(entries, model):
    if not entries:
        raise ValueError("Knowledge base is empty.")
    documents = [
        f"Topic: {entry['topic']}. Guidance: {entry['guidance']}"
        for entry in entries
    ]

    embeddings = model.encode(
        documents,
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    try:
        import faiss
        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings.astype(np.float32))
    except ImportError:
        index = NumpyIndex(embeddings.astype(np.float32))

    return index, documents



def retrieve(query, entries, model, index, documents, top_k=2):
    if top_k < 1 or not documents:
        return []
    query_embedding = model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True
    ).astype(np.float32)

    k = min(top_k, len(documents))
    scores, indices = index.search(query_embedding, k)

    results = []

    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:
            continue

        results.append({
            "score": float(score),
            "topic": entries[idx]["topic"],
            "guidance": entries[idx]["guidance"],
            "source": entries[idx].get("source", "Unknown"),
            "source_url": entries[idx].get("source_url"),
            "verified": entries[idx].get("verified", False)
        })

    return results


def main():
    entries = load_knowledge()

    if not entries:
        print("The knowledge base is empty.")
        return

    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODEL_NAME)
    index, documents = build_index(entries, model)

    query = input("Enter a tomato-growing question: ").strip()

    if not query:
        print("Please enter a question.")
        return

    results = retrieve(query, entries, model, index, documents)

    print("\nRetrieved agricultural guidance:\n")

    for number, result in enumerate(results, start=1):
        print(f"Result {number}")
        print(f"Topic: {result['topic']}")
        print(f"Guidance: {result['guidance']}")
        print(f"Source: {result['source']}")
        print(f"Verified: {result['verified']}")
        print(f"Similarity score: {result['score']:.3f}")
        print("-" * 40)


if __name__ == "__main__":
    main()
