# Benchmark Registry

`benchmark-config.json` fixes the comparison controls without inventing a model version or token budget. Those fields remain pending until the runtime used for the actual A/B run is selected and pinned.

The registry contains seven source-verified cases (CUMCM 2022 C plus COMAP 2023 MCM A/B/C/Y and ICM D/E) plus six catalog-only discovery entries. Run:

```text
python scripts/evaluate.py eligible-cases benchmarks/cases
```

Expected output includes seven eligible cases:

```json
{"eligible": [".../cumcm-2022-c/metadata.yaml", ".../mcm-2023-a/metadata.yaml", ".../mcm-2023-b/metadata.yaml", ".../mcm-2023-c/metadata.yaml", ".../mcm-2023-y/metadata.yaml", ".../icm-2023-d/metadata.yaml", ".../icm-2023-e/metadata.yaml"]}
```

To make a case eligible, verify the official statement/data source, add the required directories, add hashes and license notes, and change only that case's `source_status` to `verified` after review.

After adding the four directories, generate deterministic hash fields with:

```text
python scripts/prepare_case.py benchmarks/cases/<case-id> <verified-source-url> "<license note>"
```

The command deliberately emits `source_status: unverified`; a human/source-verification step must promote it only after checking the official statement and attachments.

The current runner environment is known to execute `codex exec` non-interactively with `gpt-5.6-sol`; Group A/B refs are pinned in `benchmark-config.json`. The CLI exposes no hard token-cap option, so equal token budget cannot be enforced at invocation time; actual input/output usage must be recorded per run and interpreted as a protocol limitation.
