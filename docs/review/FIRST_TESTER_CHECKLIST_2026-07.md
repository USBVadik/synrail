# First Tester Checklist

A 10-minute path for a first external tester. If you use Claude Code, Cursor,
Codex, Aider, or Gemini CLI, this is the fastest way to tell us whether Synrail
is useful or just in the way.

The deeper protocol lives in `FIRST_TESTER_PROTOCOL_001.md`; this file is the
short runnable version.

## Setup (about 2 minutes)

- [ ] `git clone https://github.com/USBVadik/synrail`
- [ ] `cd synrail`
- [ ] macOS/Linux: `make install-dev`
- [ ] Windows PowerShell: `py -3 -m venv .venv`, then upgrade pip and install:
      `.\.venv\Scripts\python.exe -m pip install --upgrade pip` and
      `.\.venv\Scripts\python.exe -m pip install -e ".[dev]" -c constraints-dev.txt`
- [ ] Add this checkout's venv scripts directory to the current shell `PATH`
      (`export PATH="$PWD/.venv/bin:$PATH"` on macOS/Linux, or
      `$env:Path = "$(Resolve-Path .venv\Scripts);$env:Path"` in PowerShell)
- [ ] `synrail --help` prints the command list
- [ ] macOS/Linux: `make demo`; Windows: run
      `./examples/false-green-demo/run_demo.sh` from Git Bash
- [ ] The demo shows a blocked false-green claim becoming accepted

## Read the wedge (about 1 minute)

- [ ] Read the first screen of `README.md`
- [ ] In one sentence, write down what you think Synrail is for
- [ ] Note whether that matches what the demo showed

## One real bounded task (about 5 minutes)

- [ ] Pick one small real change in any local repo (a typo fix, a small function)
- [ ] Change directory to that target repository root
- [ ] `synrail start --ephemeral "one sentence describing the change"`
- [ ] Make the change with your coding agent
- [ ] Put the proof in the `final_result.json` path printed by `start`
- [ ] `synrail check --ephemeral`
- [ ] If non-green, follow only the one repair step it names, then run
      `synrail check --ephemeral` again
- [ ] Stop only when it prints `Status: Accepted`
- [ ] `synrail cleanup --ephemeral` removes the test artifacts

## Tell us what happened (about 2 minutes)

Open one issue using the matching template:

- [ ] Caught or missed a real false-green? Use the `False-green case` template
- [ ] Confusing install, check, repair, or acceptance output? Use `Confusing output`
- [ ] Tried the demo or one real task? Use `Alpha feedback`

## The four questions we most want answered

- [ ] What problem did you think Synrail solves?
- [ ] Did it catch a real false-green or proof mismatch?
- [ ] Did the one repair step actually help?
- [ ] Was the overhead worth it for that task, or would a plain CI check have been enough?
