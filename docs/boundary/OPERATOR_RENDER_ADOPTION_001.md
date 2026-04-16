# OPERATOR_RENDER_ADOPTION_001

## Purpose

Measure whether the new human-readable operator render is actually reducing reading tax without dropping the key operator truth.

## Artifacts

The first render-adoption slice now lives at:

- `tools/reference/synrail_operator_render_adoption_v0.py`
- `tools/reference/synrail_operator_render_adoption_delta_v0.py`
- `schemas/operator_render_adoption_record_v0.schema.json`
- `schemas/operator_render_adoption_delta_v0.schema.json`
- `fixtures/operator_render_adoption/record_brief.json`
- `fixtures/operator_render_adoption/record_chain.json`
- `fixtures/operator_render_adoption/delta.json`

## What it measures

This slice compares:

1. the repairable recovery brief
- source:
  - `fixtures/operator_brief_run_002/operator_brief.json`
- render:
  - `fixtures/operator_render_run_001/operator_render.md`

2. the stop-ending operator chain
- source:
  - `fixtures/operator_brief_chain_run_002/operator_brief_chain.json`
- render:
  - `fixtures/operator_render_run_002/operator_render.md`

The current measurement is intentionally narrow:

- line-count reduction
- preservation of key operator markers

## Current honest result

Brief render:

- `source_line_count = 63`
- `render_line_count = 42`
- `line_reduction = 21`
- `truth_preserved = true`

Chain render:

- `source_line_count = 88`
- `render_line_count = 61`
- `line_reduction = 27`
- `truth_preserved = true`

Aggregate delta:

- `total_line_reduction = 48`
- `truth_preserved_all = true`
- `render_shorter_all = true`
- `verdict = READING_TAX_REDUCED_WITHOUT_TRUTH_LOSS`

## Why this matters

This is the first bounded answer to the right operator-layer question:

- did we make the layer easier to read, or only nicer-looking?

The current answer is good enough to keep the render layer alive:

- it is shorter
- it preserves the required operator markers
- and it still stays strictly derived from the runtime-owned brief surfaces

## Current reading

The shortest honest reading is:

- the render layer is not only prettier
- on the first two measured cases it is actually shorter and still preserves the key operator truth
- so it currently looks like a real reading-tax reduction rather than ornamental formatting
