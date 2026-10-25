
import json
from pathlib import Path

from sentence_transformers import SentenceTransformer
import faiss
import numpy as np


BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_FILE = BASE_DIR / "data" / "tomato_knowledge.json"

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def load_knowledge():
    with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def build_index(entries, model):
    documents = [
        f"Topic: {entry['topic']}. Guidance: {entry['guidance']}"
        for entry in entries
    ]

    embeddings = model.encode(
        documents,
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings.astype(np.float32))

    return index, documents


def retrieve(query, entries, model, index, documents, top_k=2):
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
            "verified": entries[idx].get("verified", False)
        })

    return results


def main():
    entries = load_knowledge()

    if not entries:
        print("The knowledge base is empty.")
        return

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
