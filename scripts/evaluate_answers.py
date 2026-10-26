
import json
import sys
from pathlib import Path

import requests
from sentence_transformers import SentenceTransformer

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR / "scripts"))

from retrieve_knowledge import load_knowledge, build_index, retrieve


CASES_FILE = PROJECT_DIR / "data" / "answer_evaluation_cases.json"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
OLLAMA_URL = "http://localhost:11434/api/chat"
LLM_NAME = "llama3.2:3b"


def load_cases():
    with open(CASES_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def generate_answer(question, evidence):
    prompt = f"""
You are a cautious agricultural advisory assistant specializing
in tomato plants.

Answer the farmer's question using only the supplied evidence.
Do not add possible causes that are not covered by the evidence.
If the evidence is insufficient, say so.
Do not invent facts, sources, URLs, or treatment dosages.
Yellow leaves alone do not confirm a specific deficiency.

Retrieved evidence:
{evidence}

Farmer's question:
{question}

Give a clear, concise answer.
"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": LLM_NAME,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You provide cautious, evidence-grounded "
                        "agricultural guidance. Do not invent facts."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "options": {"temperature": 0.2}
        },
        timeout=180
    )
    response.raise_for_status()
    return response.json()["message"]["content"]


def evaluate_answer(case, answer, results):
    answer_lower = answer.lower()

    expected_topics = set(case["expected_topics"])
    retrieved_topics = {item["topic"] for item in results}

    topic_match = bool(expected_topics & retrieved_topics)

    phrase_results = {
        phrase: phrase.lower() in answer_lower
        for phrase in case.get("required_phrases", [])
    }

    forbidden_results = {
        claim: claim.lower() in answer_lower
        for claim in case.get("forbidden_claims", [])
    }

    urls_present = all(
        item.get("source_url")
        for item in results
    )

    return {
        "topic_match": topic_match,
        "required_phrases": phrase_results,
        "forbidden_claims": forbidden_results,
        "source_urls_present": urls_present
    }


def main():
    cases = load_cases()
    entries = load_knowledge()

    if not cases:
        raise ValueError("Answer evaluation dataset is empty.")

    if not entries:
        raise ValueError("Knowledge base is empty.")

    embedding_model = SentenceTransformer(MODEL_NAME)
    index, documents = build_index(entries, embedding_model)

    passed_cases = 0

    print("\nANSWER EVALUATION")
    print("=" * 60)

    for case in cases:
        results = retrieve(
            case["question"],
            entries,
            embedding_model,
            index,
            documents,
            top_k=3
        )

        evidence_parts = []

        for number, item in enumerate(results, start=1):
            evidence_parts.append(
                f"[Evidence {number}]\n"
                f"Topic: {item['topic']}\n"
                f"Guidance: {item['guidance']}\n"
                f"Source: {item['source']}\n"
                f"Source URL: {item.get('source_url', 'Not provided')}\n"
                f"Verified: {item.get('verified', False)}"
            )

        evidence = "\n\n".join(evidence_parts)

        print(f"\nCase: {case['case_id']}")
        print(f"Question: {case['question']}")

        try:
            answer = generate_answer(case["question"], evidence)
        except requests.RequestException as error:
            print(f"Could not get answer from Ollama: {error}")
            continue

        checks = evaluate_answer(case, answer, results)

        print("\nGenerated answer:")
        print(answer)

        print("\nChecks:")
        print(f"Expected topic retrieved: {checks['topic_match']}")
        print(f"Required phrases: {checks['required_phrases']}")
        print(f"Forbidden claims found: {checks['forbidden_claims']}")
        print(f"Source URLs present: {checks['source_urls_present']}")

        phrases_pass = all(checks["required_phrases"].values())
        forbidden_pass = not any(checks["forbidden_claims"].values())

        case_pass = (
            checks["topic_match"]
            and phrases_pass
            and forbidden_pass
            and checks["source_urls_present"]
        )

        print(f"Basic checks passed: {case_pass}")

        if case_pass:
            passed_cases += 1

        print("\nRetrieved sources:")
        for item in results:
            print(f"- {item['source']}: {item.get('source_url', 'Not provided')}")

        print("-" * 60)

    print("\nSUMMARY")
    print(f"Cases passed: {passed_cases}/{len(cases)}")
    print(
        "These are basic automated checks, not proof of "
        "agronomic correctness or complete evidence grounding."
    )


if __name__ == "__main__":
    main()
