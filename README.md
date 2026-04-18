# Synrail

Proof-first control kernel for agent execution.

Claims are not accepted reality without proof.
`claimed_done ≠ accepted_done` — Synrail enforces this boundary.

**New here?** Start with [Your First Synrail Run](docs/core/FIRST_RUN_GUIDE.md).

## Quick Start

```bash
# Install into a local venv (writes CLAUDE.md / GEMINI.md / AGENTS.md for agent discovery)
python3 tools/reference/synrail_install_v0.py --venv .venv --project-root "$(pwd)"

# Workflow: start → edit proof files → check → fix → check again
synrail start "Describe the bounded local change."
# edit the starter proof files under .synrail/, then:
synrail check
# if non-green, fix what check says, then rerun synrail check
```

## What It Does

- 12-state machine with 7 gates governing execution lifecycle
- Doctor readiness evaluation before work begins
- Proof bundle review instead of narrative trust
- Checkpoint save/restore of verified working state
- Continuation and handoff with bounded recovery

## Layout

- `docs/core/` — kernel contracts and truth surfaces
- `tools/reference/` — CLI and reference implementation
- `tests/` — unit and integration tests
- `fixtures/` — run artifacts and alpha test results

## Documentation

- [First Run Guide](docs/core/FIRST_RUN_GUIDE.md) — one page, five steps
- [Product Memo](docs/review/PRODUCT_MEMO_001.md) — what Synrail is and isn't
- [Technical Map](docs/review/TECHNICAL_MAP_001.md) — architecture overview
- [Known Weaknesses](docs/review/KNOWN_WEAKNESSES_001.md) — honest limits
