# Evaluation protocol

## Completed checks in this development environment

- 62 automated tests passed. They cover input validation, crop isolation, claim screening, translation guards, sensor CSV handling and HTTP integration. See the repository test run for the current count.
- Four illustrative sensor CSV rows processed successfully in English evidence-only mode.
- Twelve hand-authored pipeline cases retrieved all expected topics (including expected abstention for uncovered questions), with no cross-crop records, in the lexical evidence-only baseline.
- Both prompt configuration labels ran in the baseline, but evidence-only mode does not use those prompts. These runs cannot establish prompt-engineering effectiveness.
- Python compilation and JavaScript syntax checks passed.
- Browser visual testing was blocked: the remote browser could not reach the workspace server, and the workspace Chromium process could not create its Unix socket. HTTP integration checks are used; no successful visual-rendering check is claimed.

These are software checks on a small authored test set. They are not independent agronomic validation and must not be reported as "100% crop advisory accuracy".

## Not measured here

Ollama and model weights were not installed on the development machine. No actual model generation latency, translation fidelity, quantization comparison, peak RAM/VRAM, semantic embedding retrieval quality or physical sensor accuracy was measured. The benchmark scripts generate these results when run on a provisioned target laptop. No results are prefilled.

## Quantization setup

Use the same base model and training revision for each quantization. Download appropriate GGUF files from the model publisher while online. Check licences and publisher checksums. For example, create two local Ollama models with distinct Modelfiles:

```text
FROM /absolute/path/to/same-base-model.Q4_K_M.gguf
```

```text
FROM /absolute/path/to/same-base-model.Q8_0.gguf
```

```bash
ollama create crop-q4 -f Modelfile.q4
ollama create crop-q8 -f Modelfile.q8
python scripts/benchmark.py --models crop-q4 crop-q8 --languages en hi --styles concise structured --repeats 3 --output reports/quantization
```

Use file paths that exist on your computer. Model aliases in the commands are examples. Compare Q4 and Q8 only when the underlying model, context length, prompt, input and software are otherwise held constant.

Record laptop CPU/GPU and RAM, OS, Ollama version, exact model revision and quantization, model file hash, and whether CPU or GPU inference is used. Run without internet after installing resources to demonstrate offline operation. Keep other workloads stable. Separate a cold first load from later warm runs in analysis; the saved per-run results retain repeat indices and Ollama load-duration counters.

## What the runner records

- End-to-end wall latency, including retrieval, generation, claim screening and any translation.
- Generation throughput from Ollama `eval_count / eval_duration`, with duration converted from nanoseconds. This metric covers the first generation call, not the verifier or translator.
- Installed-model metadata and loaded-model information from Ollama `/api/tags` and `/api/ps`, when available. Quantization details appear in model metadata. Loaded `size` and `size_vram` are **not peak whole-system RAM**. Use OS process/performance monitoring separately for peak RAM/VRAM.
- Retrieved topics, crop isolation, generated/screened answers, support assessments and translation structural checks.
- Exact output consistency across repeats, which is a reproducibility measure, not correctness.
- Errors as errors, without converting missing-model runs into success scores. Out-of-coverage cases can abstain without calling a model; these are counted separately as abstentions, not generated advisories.

The runner exports `results.json`, `measurements.csv` and `human_review.csv`. Human scores remain blank until a reviewer supplies them.

## Human evaluation

Have an agronomist assess factual correctness, local applicability, actionability and missing context for every case. Rate correctness and usefulness from 1 (unusable) to 5 (fully appropriate). Have a fluent regional-language reviewer compare each translation against English, especially negation, quantities, units, qualifiers and evidence labels. Rate fidelity 1–5 and separately mark whether negations were preserved.

Automatic number, evidence-label and script checks cannot establish translation fidelity. Source vocabulary overlap cannot prove factual support. A source URL is not a source-entailment metric. Model support judgements can share the generator's mistakes.

Expand cases using independently reviewed field scenarios, including dry/wet readings, out-of-range inputs, missing calibration, unfamiliar regions, unsupported disease/treatment questions and prompt-injection attempts. Avoid using the same cases to tune prompts and to claim generalization.

## Suggested report table

| Base model / quantization | Prompt | Language | Cold/warm latency | Generation tokens/s | Model size / VRAM | Human correctness | Human fidelity |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Fill after a real run | | | | | | | |

Do not substitute the evidence-only baseline for real LLM comparisons.
