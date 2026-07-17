# Synrail

[![CI](https://github.com/USBVadik/synrail/actions/workflows/security-hygiene.yml/badge.svg)](https://github.com/USBVadik/synrail/actions/workflows/security-hygiene.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
![Python 3.11-3.14](https://img.shields.io/badge/python-3.11--3.14-blue)
![Status: Alpha](https://img.shields.io/badge/status-alpha-orange)

Synrail is a local acceptance gate for coding agents. It blocks a
false-green "done" claim until task-scoped proof is rechecked.

CI asks whether configured jobs passed. AI code review asks what looks risky in
a diff. Synrail asks a narrower question: **did this bounded agent run earn the
right to be called done?**

If proof is weak, stale, mismatched, or unverified, Synrail returns a
non-green result and one bounded repair step. It complements CI and review; it
does not replace either.

## See It In 30 Seconds

```text
Agent: fixed add(); tests pass
Agent proof: grep found the new fast-path line
$ synrail verify
Verification unit: FAIL (exit 1)
$ synrail check
Synrail: Status: Verification Failed
Agent: repaired the behavior, not the story
$ synrail verify
Verification unit: GREEN
$ synrail check
Synrail: Status: Accepted
```

![Synrail false-green demo](examples/false-green-demo/assets/synrail-false-green-hero.gif)

The [standalone demo](examples/false-green-demo/README.md) runs a real failing
unit test beside plausible `grep` proof. The agent stays blocked until the
operator-approved behavior check is green. For social embeds, use the [MP4
asset](examples/false-green-demo/assets/synrail-false-green-hero.mp4).

## Try It In 2 Minutes

```bash
git clone https://github.com/USBVadik/synrail
cd synrail
make install-dev
make demo
```

`make demo` is disposable: it does not touch your project. Synrail supports
CPython 3.11-3.14. Windows setup is in the [First Run Guide](docs/core/FIRST_RUN_GUIDE.md).

## Pick The Smallest Useful Lane

| If you need to... | Start here |
| --- | --- |
| See Synrail catch a false-green claim | [`make demo`](examples/false-green-demo/README.md) |
| Prove one small tracked edit is real and current | [Small tracked change](docs/core/FIRST_RUN_GUIDE.md#1-prove-one-small-tracked-change) |
| Let an agent claim behavior such as "tests pass" | [Behavioral verification](docs/core/FIRST_RUN_GUIDE.md#2-enforce-a-behavioral-claim) |
| Work across many repositories without `.synrail/` in each | [Repo-clean workflow](docs/core/FIRST_RUN_GUIDE.md#3-keep-artifacts-outside-many-repositories) |

The single-file and batch record routes prove scope and current patch. A claim
about runtime behavior needs an operator-reviewed verification profile and a
fresh `synrail verify` receipt before `synrail check` can accept it.

## Is This Just Post-Review?

No. Post-review asks whether code looks correct. Synrail first decides whether
the agent is allowed to claim completion at all.

If you personally inspect every diff, run every check, and keep the whole agent
context in your head, Synrail may be unnecessary overhead. In that mode, you
are acting as Synrail manually.

Synrail helps when that manual supervision stops scaling: repeated agent runs,
long context, a failed repair, a second operator, or proof-sensitive work. It
turns "I think the agent did it" into an explicit local gate.

## What It Catches

- proof that does not match the changed files
- a recorded patch that drifts before acceptance
- a green-looking read-only proof beside a failing required test
- a changed workspace after a previously green behavioral check
- an incomplete repair handoff without one bounded next move

## What It Does Not Claim

- It is not a code reviewer, CI replacement, hosted orchestrator, or generic
  automation platform.
- It does not prove universal agent correctness.
- Its local receipt is not a hostile same-user security boundary: an agent
  sharing the operator account can reach project files and local user state.
  Use a required CI check on an agent-inaccessible surface for that boundary.
- It is most useful when a false-green costs more than running the gate.

## The Everyday Loop

For one existing tracked file:

```bash
synrail start "Describe the bounded local change."
# make the change and run the project's normal check
synrail record path/to/file \
  --summary "Describe the concrete bounded result." \
  --verify "grep -n 'needle' path/to/file"
synrail check
```

For a small clean-start batch of up to 32 existing tracked files:

```bash
synrail record --all-modified \
  --summary "Describe the concrete bounded result across the tracked files."
synrail check
```

`record` writes proof, not acceptance. `check` is the only command that can
return `Status: Accepted`. The [First Run Guide](docs/core/FIRST_RUN_GUIDE.md)
shows the complete, copyable routes and what to do when a run is non-green.

## Where It Fits

| Layer | Primary question | Typical output |
| --- | --- | --- |
| Agent instructions or skills | How should the agent work? | guidance inside a session |
| CI | Did configured jobs pass? | branch or pull-request checks |
| AI code review | What looks risky in this diff? | findings and suggested fixes |
| Synrail | Did this bounded run earn "done"? | `Accepted`, or a blocker plus one repair step |

These layers are complementary. Synrail binds task scope, changed files,
rechecked proof, and closure around a local agent run.

## Docs

- [First Run Guide](docs/core/FIRST_RUN_GUIDE.md) - install and four real workflows
- [Behavioral profiles](docs/advanced/VERIFICATION_PROFILES.md) - make a test or runtime claim enforceable
- [Repo-clean workflows](docs/advanced/REPO_CLEAN_WORKFLOWS.md) - ephemeral artifacts, multi-repo QA, and Windows notes
- [Docs Map](docs/README.md) - current user docs versus maintainer and historical material

## Feedback

- Real false-green caught or missed? Open a [False-green case](https://github.com/USBVadik/synrail/issues/new?template=false_green_case.yml).
- Confusing install, check, repair, or acceptance output? Open [Confusing output](https://github.com/USBVadik/synrail/issues/new?template=confusing_output.yml).
- Tried one real task? Open [Alpha feedback](https://github.com/USBVadik/synrail/issues/new?template=alpha_feedback.yml).

## Development

```bash
make smoke
make verify
```

`make verify` runs compile, tests, Ruff, coverage visibility, and dependency
audit. For a container smoke path:

```bash
docker build -t synrail-demo .
docker run --rm synrail-demo synrail --help
```

Synrail is licensed under the [Apache License 2.0](LICENSE).
