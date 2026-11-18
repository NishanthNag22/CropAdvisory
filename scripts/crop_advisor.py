"""Command line interface for the same pipeline used by the web app."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from crop_advisory.engine import advise, AdvisoryError, LANGUAGES

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--crop", choices=["tomato", "rice", "wheat", "cotton"], default="tomato")
    for name in ("region", "soil-type", "growth-stage", "symptoms", "season", "production-system", "timestamp", "weather-timestamp", "weather-source", "weather-notes"):
        parser.add_argument("--" + name, default="")
    parser.add_argument("--question")
    parser.add_argument("--moisture", type=float)
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--ph", type=float)
    parser.add_argument("--temperature-unit", default="°C")
    parser.add_argument("--moisture-unit", default="% VWC")
    parser.add_argument("--calibrated", choices=["true", "false", "unknown"], default="unknown")
    for field in ("rainfall-24h-mm", "forecast-rainfall-mm", "humidity", "max-reading-age-hours"):
        parser.add_argument("--" + field, type=float)
    parser.add_argument("--language", default="en", choices=list(LANGUAGES))
    parser.add_argument("--model", default=None)
    parser.add_argument("--mode", default="llm", choices=["llm", "evidence"])
    args = vars(parser.parse_args())
    if args["question"] is None:
        args["question"] = input("Ask your crop-growing question: ").strip()
    try:
        result = advise(args, model=args["model"], mode=args["mode"])
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, AdvisoryError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
