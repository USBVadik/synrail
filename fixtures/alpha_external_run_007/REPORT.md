# Alpha External Run 007

- Tester: Codex
- Agent: Codex / manual Synrail restore probe
- Task: Validate whether Synrail `save` / `restore` can bring a known-good workspace back after a deliberate break during an in-progress run.
- Project: alpha retry service fixture (clean fixed workspace derived from run 006, Synrail 4790036)
- Start time: 2026-04-18T08:38:58+00:00
- End time: 2026-04-18T08:39:42+00:00
- Elapsed minutes: 0.7 min (44s)
- Check iterations: 1
- Final outcome: RESTORE_FAILED_FOR_MID_RUN_FALLBACK
- Got lost moments:
  - Baseline was genuinely green: visible tests passed and the hidden oracle passed before the run started.
  - `synrail save` did not create a verified restore point; it returned `{"result": "BLOCKED", "verification_status": "FAILED"}` and only saved a fallback checkpoint.
  - The guidance said `synrail confirm-restore`, but `confirm-restore` immediately answered `Synrail could not find a restore point to confirm.`
  - After deliberately breaking `api_service/retry_logic.py`, visible tests and the hidden oracle both failed as expected.
  - `synrail check` did not talk about rollback at all; it only complained that proof artifacts were still missing for the controlled run.
  - `synrail restore` returned `{"result": "BLOCKED", "event_type": "RESTORE", "rollback_status": "NOT_NEEDED"}` and the workspace stayed broken. Restored tests still failed, and the hidden oracle still failed.
- Verdict: This is a real alpha bug. In this realistic mid-run scenario, `save`/`confirm-restore`/`restore` did not recover the last known-good state. Right now this path does not yet prove an advantage over a plain manual rollback.
