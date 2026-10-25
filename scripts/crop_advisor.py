
import json
from pathlib import Path

import requests

from retrieve_knowledge import (
    load_knowledge,
    build_index,
    retrieve,
)
from sentence_transformers import SentenceTransformer


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
        question, entries, embedding_model, index, documents, top_k=3
    )

    evidence = "\n".join(
        f"- Topic: {item['topic']}\n"
        f"  Guidance: {item['guidance']}\n"
        f"  Source: {item['source']}\n"
        f"  Verified: {item['verified']}"
        for item in results
    )

    prompt = f"""
You are a cautious tomato-growing advisory assistant.

Answer the user's question using the retrieved evidence below.

Rules:
1. Do not invent facts or claim that unverified evidence is authoritative.
2. The supplied knowledge entries are currently unverified.
3. If the evidence is insufficient, say so clearly.
4. Give practical observations the farmer can check.
5. Do not prescribe fertilizer or pesticide dosages without reliable evidence.
6. Separate evidence-based statements from possible explanations.

Retrieved evidence:
{evidence}

Farmer's question:
{question}

Provide a clear, beginner-friendly answer.
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
            "You are an agricultural crop advisory assistant "
            "specializing in tomato plants. You answer questions "
            "about plant health, soil, irrigation, nutrients, "
            "weather, and crop management. The word 'health' here "
            "means plant health, not human or animal medicine. "
            "Never refuse an agricultural question as medical advice. "
            "Use the supplied evidence cautiously. The knowledge "
            "entries are unverified, so clearly state when evidence "
            "is insufficient. Do not invent facts or pesticide "
            "dosages. Give a practical, clear answer to the farmer."
        )
    },
    {
        "role": "user",
        "content": prompt
    }
],
"stream": False

            },
            timeout=180
        )
        response.raise_for_status()
        answer = response.json()["message"]["content"]
        print("CROP ADVISORY\n")
        print(answer)

    except requests.RequestException as error:
        print("Could not connect to Ollama.")
        print("Make sure Ollama is running and the model is installed.")
        print(f"Details: {error}")


if __name__ == "__main__":
    main()
