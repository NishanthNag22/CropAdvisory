
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



from evaluate_answers import evaluate_answer


def test_answer_evaluation_accepts_supported_answer():
    case = {
        "expected_topics": ["nitrogen_deficiency"],
        "required_phrases": ["yellow", "nitrogen"],
        "forbidden_claims": [
            "yellow leaves always confirm nitrogen deficiency"
        ]
    }

    answer = (
        "Nitrogen deficiency may cause older leaves to turn yellow. "
        "Yellow leaves alone do not confirm nitrogen deficiency."
    )

    results = [
        {
            "topic": "nitrogen_deficiency",
            "source_url": "https://example.com/source"
        }
    ]

    checks = evaluate_answer(case, answer, results)

    assert checks["topic_match"] is True
    assert all(checks["required_phrases"].values())
    assert not any(checks["forbidden_claims"].values())
    assert checks["source_urls_present"] is True


def test_answer_evaluation_detects_missing_source_url():
    case = {
        "expected_topics": ["soil_pH"],
        "required_phrases": [],
        "forbidden_claims": []
    }

    answer = "Tomatoes grow well within the tested pH range."

    results = [
        {
            "topic": "soil_pH",
            "source_url": None
        }
    ]

    checks = evaluate_answer(case, answer, results)

    assert checks["topic_match"] is True
    assert checks["source_urls_present"] is False


def test_answer_evaluation_detects_forbidden_phrase():
    case = {
        "expected_topics": ["nitrogen_deficiency"],
        "required_phrases": ["nitrogen"],
        "forbidden_claims": [
            "yellow leaves always confirm nitrogen deficiency"
        ]
    }

    answer = "Yellow leaves always confirm nitrogen deficiency."

    results = [
        {
            "topic": "nitrogen_deficiency",
            "source_url": "https://example.com/source"
        }
    ]

    checks = evaluate_answer(case, answer, results)

    assert any(checks["forbidden_claims"].values())
