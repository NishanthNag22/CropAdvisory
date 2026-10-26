
from pathlib import Path

import requests
from sentence_transformers import SentenceTransformer

from retrieve_knowledge import load_knowledge, build_index, retrieve


BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
OLLAMA_URL = "http://localhost:11434/api/chat"
LLM_NAME = "llama3.2:3b"


def main():
    entries = load_knowledge()

    if not entries:
        print("Knowledge base is empty.")
        return

    embedding_model = SentenceTransformer(MODEL_NAME)
    index, documents = build_index(entries, embedding_model)

    question = input("Ask your tomato-growing question: ").strip()

    if not question:
        print("Please enter a question.")
        return

    results = retrieve(
        question,
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

    prompt = f"""
You are a cautious agricultural advisory assistant specializing
in tomato plants.

Answer the farmer using the retrieved evidence below.

Rules:
1. Use retrieved guidance as the factual basis for your answer.
2. Do not claim the evidence proves a diagnosis.
3. Do not invent facts, sources, URLs, or dosages.
4. If the evidence does not cover a possible cause, say it is
   not covered by the retrieved evidence.
5. Distinguish supported guidance from uncertainty.
6. Keep the answer practical and beginner-friendly.
7. Do not describe plant-health questions as medical advice.

Retrieved evidence:
{evidence}

Farmer's question:
{question}

Write the answer with short headings or bullet points.
Refer to evidence labels such as [Evidence 1] when relevant.
"""

    print("\nGenerating advice with Llama 3.2...\n")

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": LLM_NAME,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You provide cautious, evidence-grounded "
                            "agricultural guidance. Never invent sources "
                            "or claim unsupported facts are verified."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "stream": False,
                "options": {
                    "temperature": 0.2
                }
            },
            timeout=180
        )

        response.raise_for_status()
        answer = response.json()["message"]["content"]

        print("=" * 50)
        print("CROP ADVISORY")
        print("=" * 50)
        print(answer)

        print("\nSOURCES USED")
        print("-" * 50)

        if not results:
            print("No relevant sources were retrieved.")

        for number, item in enumerate(results, start=1):
            print(f"[Evidence {number}] {item['source']}")
            print(f"Topic: {item['topic']}")
            print(f"Verified in knowledge base: {item['verified']}")

            source_url = item.get("source_url")
            if source_url:
                print(f"URL: {source_url}")
            else:
                print("URL: Not provided")

            print()

    except requests.RequestException as error:
        print("Could not connect to Ollama.")
        print("Make sure Ollama is running and the model is installed.")
        print(f"Details: {error}")

    except (KeyError, ValueError) as error:
        print("Ollama returned an unexpected response.")
        print(f"Details: {error}")


if __name__ == "__main__":
    main()

from pathlib import Path

import requests
from sentence_transformers import SentenceTransformer

from retrieve_knowledge import load_knowledge, build_index, retrieve


BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
OLLAMA_URL = "http://localhost:11434/api/chat"
LLM_NAME = "llama3.2:3b"


def main():
    entries = load_knowledge()

    if not entries:
        print("Knowledge base is empty.")
        return

    embedding_model = SentenceTransformer(MODEL_NAME)
    index, documents = build_index(entries, embedding_model)

    question = input("Ask your tomato-growing question: ").strip()

    if not question:
        print("Please enter a question.")
        return

    results = retrieve(
        question,
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

    prompt = f"""
You are a cautious agricultural advisory assistant specializing
in tomato plants.

Answer the farmer using the retrieved evidence below.

Rules:
1. Use retrieved guidance as the factual basis for your answer.
2. Do not claim the evidence proves a diagnosis.
3. Do not invent facts, sources, URLs, or dosages.
4. If the evidence does not cover a possible cause, say it is
   not covered by the retrieved evidence.
5. Distinguish supported guidance from uncertainty.
6. Keep the answer practical and beginner-friendly.
7. Do not describe plant-health questions as medical advice.

Retrieved evidence:
{evidence}

Farmer's question:
{question}

Write the answer with short headings or bullet points.
Refer to evidence labels such as [Evidence 1] when relevant.
"""

    print("\nGenerating advice with Llama 3.2...\n")

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": LLM_NAME,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You provide cautious, evidence-grounded "
                            "agricultural guidance. Never invent sources "
                            "or claim unsupported facts are verified."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "stream": False,
                "options": {
                    "temperature": 0.2
                }
            },
            timeout=180
        )

        response.raise_for_status()
        answer = response.json()["message"]["content"]

        print("=" * 50)
        print("CROP ADVISORY")
        print("=" * 50)
        print(answer)

        print("\nSOURCES USED")
        print("-" * 50)

        if not results:
            print("No relevant sources were retrieved.")

        for number, item in enumerate(results, start=1):
            print(f"[Evidence {number}] {item['source']}")
            print(f"Topic: {item['topic']}")
            print(f"Verified in knowledge base: {item['verified']}")

            source_url = item.get("source_url")
            if source_url:
                print(f"URL: {source_url}")
            else:
                print("URL: Not provided")

            print()

    except requests.RequestException as error:
        print("Could not connect to Ollama.")
        print("Make sure Ollama is running and the model is installed.")
        print(f"Details: {error}")

    except (KeyError, ValueError) as error:
        print("Ollama returned an unexpected response.")
        print(f"Details: {error}")


if __name__ == "__main__":
    main()
