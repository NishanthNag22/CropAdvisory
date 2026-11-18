# Paper-to-project implementation map

The paper is a research design. This map separates implemented capabilities from experiments and external reviews that still have to be performed.

| Paper item | Implemented support | Evidence or remaining requirement |
| --- | --- | --- |
| Measurement value, unit, timestamp and validation state | `quality.py` normalizes fractional VWC and Fahrenheit; retains original units, timestamp, age and calibration state | Unit, timestamp, stale/future, missing and fault tests |
| Stale and faulty sensor handling | Readings older than a configurable age, future dated, explicitly uncalibrated or faulted are excluded from the decision context | Raw values remain in the audit result; unknown timestamp/calibration produces warnings |
| Sensor fault detection | Range/type checks, explicit device fault reports, out-of-order timestamps and suspected stuck readings in CSV history | Stuck detection requires an explicit sensor ID and five identical samples. Stable real conditions can cause the same pattern; this is a suspicion requiring inspection, not a diagnosis |
| Weather context | Manual/offline snapshot fields for rainfall, forecast rainfall, humidity, source, notes and timestamp | Stale or future snapshots are excluded from decision context. No live weather API is required |
| Geographic/seasonal/source-date checks | Source applicability assessment records crop, region, season, production system, review/publication dates and expiry | Explicit mismatches and expired records are excluded. Unknown metadata stays unknown; missing publication dates are not invented |
| Stronger translation validation | Numerical/label/unit and quantity-unit guards plus a separate local-model review of crop names, conditions, negation, warnings, uncertainty and meaning | Failed/unavailable regional output is withheld while English remains visible. Human review is still required |
| Structured versus unstructured prompting | `structured` uses JSON context; `unstructured` expresses the same normalized observations in prose | Shared grounding and output instructions isolate input representation. Evidence-only mode cannot measure prompt quality |
| Direct multilingual comparison | Research-only `direct` arm generates in the target language and screens claims; `translate` is the normal English-then-translate arm | Direct output is evaluated against the same expert rubric, not automatically assigned a translation-fidelity score against an unrelated English response |
| Precision baseline and quantization arms | Benchmark accepts FP16/higher-precision, Q8 and Q4 aliases, exact model metadata and optional GGUF hashes | Weights must be installed by the operator; use the same base revision and tokenizer |
| Expert-reviewed dataset | Versioned 20-case synthetic dataset with fixed development/evaluation splits and draft rubrics; reviewer CSV import | These cases are **not expert reviewed**. An agronomist must supply/approve reference answers and scoring. Splits were inspected during implementation and are not a blind independent benchmark |
| Correctness, critical errors, completeness and usefulness | Human review fields, validated import and summaries with actual numerators and denominators | Unfilled reviews produce no human score |
| Median/p95 latency and throughput | Per-run wall latency, token counters and grouped summaries | Wall timing includes retrieval, checks, translation and measurement/metadata overhead |
| Peak resident memory and GPU memory | Sampled RSS over client and explicitly selected process trees; NVIDIA process memory when tooling exists | Sampling may miss short peaks; shared RSS pages may be counted repeatedly. Include Ollama's process tree for server memory |
| Energy if measurable | Linux RAPL CPU-package energy delta, including one counter wrap | Null when unavailable. Package energy includes other system work; it is not model-only or full-device energy |
| Confidence intervals and paired analysis | Wilson intervals for case-level proportions; seeded paired bootstrap of per-case latency and reviewer correctness differences | Intervals describe this selected sample, not general agricultural accuracy |
| Inter-rater agreement | Cohen's kappa on matching human-rated outputs | Requires at least two actual reviewers; absent/degenerate ratings return no meaningful kappa |
| Quality/resource curves | Plot generator consumes real human correctness scores and measured latency/memory | No human scores means no quality curve is produced |
| Offline robustness | Loopback-only client guard, missing-resource handling and optional host-adapter precondition | Guard does not sandbox the separate Ollama daemon. Disconnect/OS-isolate both local processes for an actual offline demonstration |
| Reproducibility | Dataset/module hashes, exact generation messages, decoding settings, dependency and model metadata, raw drafts and output records | Record target CPU/GPU, model revision and hardware configuration when running the real experiment |

## What cannot be supplied by implementation alone

The code does not turn synthetic records into expert-labelled cases, generate genuine bilingual reviewer ratings, measure hardware that is not connected, or prove quantization quality without running model weights. Those are research activities. GPTQ and QLoRA remain related-work references; this project does not claim to implement either algorithm or to fine-tune a model.
