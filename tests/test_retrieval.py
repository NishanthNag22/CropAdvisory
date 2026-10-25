
import sys
from pathlib import Path

import numpy as np

# Allow the test to import scripts from the project directory.
PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR / "scripts"))

from retrieve_knowledge import load_knowledge, build_index, retrieve


class FakeModel:
    """A small test model that avoids downloading an embedding model."""

    def encode(
        self,
        sentences,
        convert_to_numpy=True,
        normalize_embeddings=True
    ):
        if len(sentences) > 1:
            embeddings = np.eye(3, dtype=np.float32)[:len(sentences)]
        else:
            embeddings = np.array([[1, 0, 0]], dtype=np.float32)

        return embeddings


def test_knowledge_base_loads():
    entries = load_knowledge()

    assert len(entries) > 0
    assert all("topic" in entry for entry in entries)
    assert all("guidance" in entry for entry in entries)


def test_index_builds():
    entries = load_knowledge()
    model = FakeModel()

    index, documents = build_index(entries, model)

    assert index.ntotal == len(entries)
    assert len(documents) == len(entries)


def test_retrieval_returns_results():
    entries = load_knowledge()
    model = FakeModel()
    index, documents = build_index(entries, model)

    results = retrieve(
        "What should I check for tomato plants?",
        entries,
        model,
        index,
        documents,
        top_k=2
    )

    assert len(results) == 2
    assert all("topic" in result for result in results)
    assert all("guidance" in result for result in results)
    assert all("score" in result for result in results)
