# CropAdvisory

An offline-ready, multilingual, sensor-based agricultural advisory application. The application supports **tomato, rice, wheat and cotton** with crop-filtered references, local Ollama inference, claim screening and regional-language output. Tomato is the first prototype crop, not the project's scope limit.

## Run it

Requires Python 3.10+ and a browser. The default web application uses the Python standard library; no Python packages or cloud API keys are required.

```bash
git clone https://github.com/NishanthNag22/CropAdvisory.git
cd CropAdvisory
python app.py
```

Open **http://127.0.0.1:8501**. On Windows, use `py app.py` if `python` is unavailable. Stop with Ctrl+C.

For an immediate demo, click **Try an irrigation example**, then **Generate advisory**. This selects the English **Evidence-only preview**, which displays source guidance without model inference. It works without Ollama and is not a generated recommendation.

### Enable local LLM advice and Hindi

Install [Ollama](https://ollama.com/download) from its official website. While connected to the internet, install model weights once:

```bash
ollama pull llama3.2:3b
ollama serve
```

If Ollama is already running in the desktop app, a second `ollama serve` is unnecessary. Start `python app.py`, choose **Local LLM**, and enter an installed model name. Choose Hindi, Kannada, Tamil or Telugu to translate the screened English advice with the local model. Llama 3.2 is retained from the original prototype; output quality in each language must be evaluated rather than assumed. Use another preinstalled multilingual Ollama model when needed.

The browser, evidence files and application assets run locally. Model and optional embedding weights must be installed **before** disconnecting the internet. Cloud model tags are rejected. No model weights are included in this repository.

## What is implemented

- Manual and CSV sensor inputs with timestamp/calibration/fault states, unit conversion (Fahrenheit and fractional VWC), stale/future checks, and preservation of raw measurements for audit. Unusable readings are withheld; missing readings remain missing.
- Crop, region, season, production system, soil type, growth stage, symptoms and offline weather snapshots form the model context. Rainfall, forecast rainfall and humidity include timestamp/source metadata.
- Crop-filtered retrieval screens region, season, production system and date metadata. Explicit mismatches/expired sources are excluded and unknown metadata is disclosed. It preserves sources, regional scope and review dates. The default keyword/topic baseline requires no model download. An optional MiniLM + FAISS backend uses cached local model files.
- Local quantized model inference through Ollama; structured JSON and an unstructured prose input baseline with shared output instructions, plus a separate concise option.
- Claim-level screening: rules reject unsupported dosages and narrow contradictions; a local-model reviewer assesses paraphrased claims against supplied evidence. Unassessed and unsupported claims are withheld. A failed reviewer falls back to source guidance.
- Hindi, Kannada, Tamil and Telugu output with number/label/script/unit checks and a local-model semantic assessment of crop names, conditions, negation, warnings and uncertainty. Failed translation is withheld; original English remains visible. These are fallible automated assessments, not human validation.
- Local web interface, JSON export, CLI and CSV ingestion, including sensor-ID-based suspected stuck/out-of-order detection. Benchmark arms include English-then-translate and research-only direct multilingual generation. Resource monitoring, statistical analysis, reviewer imports and offline probes are included.
- Tests, CI configuration, blank expert-review forms and validated annotation import, plus documented evaluation limitations.

## Supported evidence coverage

| Crop | Included evidence | Regional/production scope |
| --- | --- | --- |
| Tomato | Soil pH, irrigation, nitrogen-deficiency symptoms | TNAU guidance, Tamil Nadu |
| Rice | Water management and critical growth stages | Transplanted rice, Tamil Nadu |
| Wheat | Irrigation, growth stages, soil-test-led nutrition | TNAU guidance, Tamil Nadu |
| Cotton | Irrigation and critical growth stages | Irrigated cotton, Tamil Nadu |

The bundled knowledge base is deliberately small. Multi-crop support does **not** mean complete coverage of every disease, region or crop condition. Temperature thresholds and general moisture targets are absent. Unknown publication dates or season applicability remain explicit; a metadata match does not establish field validity. The system must abstain when its references do not cover a question. Region is context for applicability checks, not a claim of validated recommendations for that region. Uncalibrated raw sensor percentages cannot be substituted for VWC.

## Command line and CSV logs

```bash
python scripts/crop_advisor.py --crop rice --question "How does flowering affect water needs?" --moisture 32 --temperature 29 --language hi
python scripts/crop_advisor.py --crop wheat --question "What should guide irrigation?" --mode evidence
python scripts/batch_advice.py data/sensor_samples.csv --mode evidence --output reports/batch.jsonl
```

Use `data/sensor_samples.csv` as the import format. Values are illustrative, **not field measurements**. Invalid rows retain their row number and error; processing continues for other rows. For actual hardware, log calibrated values in this format or POST readings to `/api/advice`. No physical sensor was connected or validated in this development environment.

### Optional semantic RAG

```bash
python -m pip install -r requirements-semantic.txt
```

Download `sentence-transformers/all-MiniLM-L6-v2` into a local folder during setup. Set environment variables before starting the app:

PowerShell:

```powershell
$env:RETRIEVAL_BACKEND="semantic"
$env:EMBEDDING_MODEL_PATH="C:\models\all-MiniLM-L6-v2"
python app.py
```

Bash:

```bash
export RETRIEVAL_BACKEND=semantic
export EMBEDDING_MODEL_PATH=/absolute/path/to/all-MiniLM-L6-v2
python app.py
```

Inference uses `local_files_only=True`; it will fail clearly if assets are missing. No automatic download is attempted by the application. This English embedding model expects English farmer questions; the current UI's language selector controls the **answer language**. It is not a multilingual query translator.

## Evaluation

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python scripts/benchmark.py
```

The last command evaluates the evidence-only baseline on the fixed evaluation split of the versioned synthetic cases and both input-representation labels. Since no LLM is used, those labels do not demonstrate a prompt-quality difference. Expert review is pending and explicitly recorded in the dataset metadata.

For actual quantization comparisons, install **different quantizations of the same base model** in Ollama under distinct local names, then run:

```bash
python scripts/benchmark.py --models crop-fp16 crop-q8 crop-q4 --languages en hi --styles structured unstructured --strategies translate direct --repeats 3 --output reports/quantization
```

`crop-fp16`, `crop-q4` and `crop-q8` are example local aliases, not pre-existing downloadable tags. See [evaluation guide](docs/EVALUATION.md) for GGUF setup, measurements and human scoring. Failures stay failures; the tool does not substitute generated results when a model is missing. JSON output includes installed-model metadata, inference counters, wall latency and loaded-model memory information. CSV output includes measurements and **blank** human review fields.

## Configuration

| Environment variable | Default | Purpose |
| --- | --- | --- |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | Local HTTP Ollama address only |
| `OLLAMA_MODEL` | `llama3.2:3b` | Default installed local model |
| `RETRIEVAL_BACKEND` | `lexical` | `lexical` or `semantic` |
| `EMBEDDING_MODEL_PATH` | unset | Preinstalled model folder for semantic retrieval |

The UI's model field can override `OLLAMA_MODEL`. The app binds to localhost. Inputs are not stored by the web server; download an advisory to retain it. CSV/benchmark runs explicitly save results to their output directories, which are ignored by Git.

## Documentation

- [Architecture and API](docs/ARCHITECTURE.md)
- [Evaluation protocol and current evidence](docs/EVALUATION.md)
- [Source provenance and knowledge extension](docs/SOURCES.md)
- [Paper-to-implementation coverage](docs/PAPER_IMPLEMENTATION.md)

Automated support judgements and translation checks can fail. They are not proof of agronomic correctness. Review claims with an agronomist and translations with a fluent speaker before real-world decisions.
