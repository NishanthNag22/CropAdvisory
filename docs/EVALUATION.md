# Evaluation protocol and commands

## Verified software checks

The expanded implementation passes **146 automated tests** after the multilingual recovery and metadata fixes. Tests cover measurement conversion and quality, source applicability, translation withholding, prompt representation, resource reporting, statistics, dataset provenance, offline client guards, and HTTP integration.

An evidence-only smoke run completed all **13 cases in the evaluation split**, for both structured and unstructured configuration labels. It retrieved the expected topics or abstained as specified. Evidence-only mode makes no LLM call: these runs test plumbing and source selection, **not prompt quality or agronomic accuracy**.

CSV ingestion, analysis export and the loopback-only evidence preview also completed. The environment did not permit inspecting network interfaces; the offline report correctly records unknown adapter state and `network_isolation_verified: false`.

No actual LLM generation, semantic translation quality, quantization quality, physical sensor accuracy, agronomist ratings or bilingual ratings have been measured here. The direct-generation and semantic-review tests use explicit model-response fixtures. A model judge's support labels are not independent expert ground truth. The earlier visual-browser check was blocked by the development environment.

## Setup

```bash
python -m pip install -r requirements-dev.txt
python -m pip install -r requirements-analysis.txt
python -m pytest -q
```

The application itself still requires only Python's standard library for lexical retrieval. Optional semantic retrieval uses `requirements-semantic.txt` and preinstalled weights.

## 1. Prepare and freeze cases

`data/research_cases.json` contains 20 synthetic authored cases, version 1.0.0, with seven development and thirteen evaluation cases. Categories include routine use, missing inputs, stale readings, faulty probes, unit conversion, stale weather, unfamiliar regions, boundary values and adversarial questions.

Each case includes a draft rubric and `expert_reviewed: false`. Reference answers are null until an agronomist supplies them. A case may be marked reviewed only with reviewer provenance. These fixed splits were inspected during implementation and therefore cannot be sold as an untouched, independent blind benchmark. Add an independently reviewed held-out set before publication claims.

Export blank case-review forms and import annotations supplied by an agronomist:

```bash
python scripts/review_dataset.py export data/research_cases.json --output reports/case-review.csv
python scripts/review_dataset.py import data/research_cases.json --annotations reports/case-review.csv --output reports/expert-reviewed-cases.json
```

A decision requires reviewer identity and a review date. Approval additionally requires a reference answer, required-point rubric and source URLs. The importer validates completeness and provenance; it cannot verify credentials or establish that a real expert performed the work. Blank forms leave review status pending. The original dataset is unchanged unless you explicitly choose to replace it.

Tune prompts on development cases. Hash and freeze an independent evaluation dataset before measuring final quality. Do not edit its answers or prompts after seeing final scores without reporting that change.

## 2. Install matched model precision variants

Use the same base model, training revision and tokenizer for a higher-precision baseline and at least two quantized variants. Create local Ollama aliases from appropriate GGUF files:

```text
FROM /absolute/path/to/same-base.F16.gguf
```

```text
FROM /absolute/path/to/same-base.Q8_0.gguf
```

```text
FROM /absolute/path/to/same-base.Q4_K_M.gguf
```

```bash
ollama create crop-fp16 -f Modelfile.fp16
ollama create crop-q8 -f Modelfile.q8
ollama create crop-q4 -f Modelfile.q4
```

These are example local aliases and file paths, not published downloadable model tags. Use a model that fits the target laptop. Record exact revision, licence, file hash, CPU/GPU, RAM, OS and runtime. Ollama metadata is collected automatically; optional `--model-files alias=/path/to/file.gguf` computes file hashes and sizes.

## 3. Run comparisons

```bash
python scripts/benchmark.py --models crop-fp16 crop-q8 crop-q4 --languages en hi --styles structured unstructured --strategies translate direct --repeats 3 --warmup-runs 1 --split evaluation --output reports/quantization
```

For Hindi/Kannada comparisons, name the languages explicitly using `hi kn`. The `direct` arm is a research arm; the normal UI continues to use English-then-translate. Direct output has no independently generated English source, so assess its adequacy against the case rubric. Do not pretend it has a measured translation-equivalence score.

The structured/unstructured arms carry the same normalized observations, source evidence, grounding rules and output instructions. The separate concise option changes output instructions and is not the primary input-format ablation.

Warm-up attempts are saved separately and excluded from scored rows. A zero-warmup run is not automatically a verified cold run: unload models and record initial runtime state if a true cold-start comparison is required. Hold decoding options constant; current settings are temperature 0, seed 42, context 4096 and maximum generated tokens 800.

### Memory and energy

Pass Ollama process IDs so the monitor includes its runner children:

```bash
python scripts/benchmark.py --models crop-q4 --monitor-pids 12345 --output reports/memory
```

Replace `12345` with the real server PID. The client process is always included. Without an Ollama PID, sampled RSS is client-only and must not be described as inference-server RAM. Install `psutil` for process memory; optional NVIDIA tooling supplies sampled process GPU memory. Linux RAPL supplies CPU-package energy when readable. Unavailable measurements remain null. Sampled maxima can miss brief peaks, and process RSS can double-count shared pages.

The benchmark also records Ollama's loaded model `size` and `size_vram` where available. Those are separate from sampled process RAM and are not whole-device peak memory.

## 4. Obtain human ratings

The runner exports `human_review.csv` with output text and blank fields:

- `correct`, `critical_error`, `complete`: 0/1, with blank meaning not rated.
- Agronomic correctness, usefulness and translation fidelity: integer 1–5, or blank.
- `reviewer`, negation preservation and notes.

Have an agronomist score advice and context applicability. Have fluent regional-language reviewers assess terminology, conditions, quantities, units, negation and uncertainty. Use two or more reviewers for agreement analysis. Copy the sheet for additional reviewers, then combine their rows with distinct reviewer identifiers. Never fill scores using synthetic assumptions or software-test counts.

## 5. Analyze real results

```bash
python scripts/analyze_experiments.py reports/quantization/results.json --reviews reports/quantization/human_review.csv --compare-models crop-fp16 crop-q4 --output reports/analysis
```

Outputs include median/p95 latency, throughput, retrieved-topic counts, human summaries, paired bootstrap differences and separate unweighted Cohen kappa for correctness and translation-fidelity ratings. Repeated outputs are clustered by case. For binary case correctness/completeness, a case passes only if all its reviewed repeats pass; a case has a critical error if any reviewed repeat contains one. Wilson intervals use these case-level counts. Paired bootstrap comparisons use matched cases under the same language/style/strategy and reviewer.

Quality/resource plots require actual human scores and matplotlib. Without ratings, analysis produces no human accuracy or quality curve. Report language-specific findings, failure cases and source limitations. A retrieval hit is not an agronomic-correctness judgement.

## 6. Check offline behaviour

```bash
python scripts/offline_check.py --mode evidence
python scripts/offline_check.py --mode llm --model crop-q4 --require-network-disconnected
```

The client guard prevents non-loopback TCP connections and external DNS in the Python process. It **does not isolate Ollama**. The strict option also requires no active non-loopback interfaces as reported by psutil and fails if adapters cannot be inspected. For the paper's real offline demonstration, disconnect networking or use OS isolation for both processes after installing all weights and local knowledge. Capture the target-machine state and results. Do not call a successful client guard a complete hardware offline experiment.

## Recovery checks for reported multilingual failures

The claim parser ignores recognised headings and list markers before sentence splitting. Reviewer calls contain at most three claims, with a 2048-token output budget and 8192-token context. Missing/invalid claim assessments are retried once individually; completed valid assessments survive failed neighbours. Unresolved claims remain withheld.

Normal generation retains its 800-token output budget and 4096-token context. Translation uses a separate 2048-token budget and 8192-token context. A truncated translation is discarded and retried as complete sentence chunks, with 3072 tokens per chunk and one final 4096-token retry if needed. Translation semantic review uses 1024 output tokens and 8192 context tokens. Output budgets and completion reasons are recorded in metrics. The UI reports specific failure reasons while preserving English.

Regression fixtures replay the two reported English drafts. Fixed model-response fixtures exercise successful retry and exhausted-retry paths for Hindi and Kannada. These tests establish failure-handling behaviour, **not real language fluency or translation accuracy**.

Run actual local-model checks on the target laptop after updating and restarting the app:

```bash
python scripts/check_languages.py --model llama3.2:3b
```

The command checks Hindi and Kannada sequentially, prints each result and saves `reports/language-check.json` after each language. A failed automated check yields exit code 1 and retains the reason. Have fluent speakers review accepted translations; increasing token limits cannot guarantee that a model knows a language.

### Citation and technical-value preservation

Citation-only fragments are attached to the preceding substantive claim and are never independently reviewed or rendered as advisory text. Translation receives complete text chunks with citation metadata removed; the application reattaches the source IDs belonging to each chunk. The model cannot select replacement evidence IDs.

Numbers and canonical technical terms (including pH, VWC and measurement units) are replaced with opaque letter-only markers before translation. Every marker must survive exactly once before its original value can be restored. Missing/duplicated markers and unexpected citations trigger bounded retries and otherwise withhold the translation. No missing measurement is silently invented or appended.

Unicode decimal digits and compatibility symbols are normalized for equivalent-value comparisons (for example, Kannada decimal glyphs or the Celsius compatibility character). Numerical and citation multiplicity is checked, so duplicated or changed values remain failures. Semantic review compares the natural-language text; citation metadata is checked independently by the application. Raw candidate text is retained only in the JSON audit metrics and is not shown as advice. These candidates can be incomplete or invalid.
