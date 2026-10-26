
import json
import sys
from pathlib import Path

from sentence_transformers import SentenceTransformer

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR / "scripts"))

from retrieve_knowledge import load_knowledge, build_index, retrieve


CASES_FILE = PROJECT_DIR / "data" / "evaluation_cases.json"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def load_cases():
    with open(CASES_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def main():
    entries = load_knowledge()
    cases = load_cases()

    if not entries:
        raise ValueError("Knowledge base is empty.")

    if not cases:
        raise ValueError("Evaluation dataset is empty.")

    model = SentenceTransformer(MODEL_NAME)
    index, documents = build_index(entries, model)

    top1_hits = 0
    top2_hits = 0

    print("\nRETRIEVAL EVALUATION")
    print("=" * 60)

    for number, case in enumerate(cases, start=1):
        expected = set(case["expected_topics"])

        results = retrieve(
            case["question"],
            entries,
            model,
            index,
            documents,
            top_k=2
        )

        retrieved_topics = [
            result["topic"] for result in results
        ]

        top1_match = (
            bool(retrieved_topics)
            and retrieved_topics[0] in expected
        )
        top2_match = bool(set(retrieved_topics) & expected)

        top1_hits += int(top1_match)
        top2_hits += int(top2_match)

        print(f"\nCase {number}: {case['question']}")
        print(f"Expected topics: {sorted(expected)}")
        print(f"Retrieved topics: {retrieved_topics}")
        print(f"Top-1 hit: {top1_match}")
        print(f"Top-2 hit: {top2_match}")

    total = len(cases)

    print("\n" + "=" * 60)
    print(f"Total cases: {total}")
    print(f"Top-1 accuracy: {top1_hits / total:.1%}")
    print(f"Top-2 accuracy: {top2_hits / total:.1%}")
    print(
        "Note: These metrics use a small, manually created "
        "evaluation set and are not a general performance claim."
    )


if __name__ == "__main__":
    main()
