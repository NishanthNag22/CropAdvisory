
import json
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR / "scripts"))

from evaluate_retrieval import load_cases


def test_evaluation_cases_load():
    cases = load_cases()

    assert len(cases) == 4
    assert all(case.get("question") for case in cases)
    assert all(case.get("expected_topics") for case in cases)


def test_expected_topics_exist_in_knowledge_base():
    knowledge_path = PROJECT_DIR / "data" / "tomato_knowledge.json"

    with open(knowledge_path, "r", encoding="utf-8") as file:
        entries = json.load(file)

    available_topics = {entry["topic"] for entry in entries}

    for case in load_cases():
        assert set(case["expected_topics"]).issubset(available_topics)
