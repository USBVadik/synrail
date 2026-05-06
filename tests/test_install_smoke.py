#!/usr/bin/env python3
"""Install smoke for the supported Synrail tester path."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER = REPO_ROOT / "tools" / "reference" / "synrail_install_v0.py"


class InstallSmokeTests(unittest.TestCase):
    def _assert_installed_start_path(self, synrail_bin: Path, project_root: Path) -> None:
        artifact_root = project_root / ".synrail"

        help_result = subprocess.run(
            [str(synrail_bin), "start", "--help"],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("--project-root", help_result.stdout)
        self.assertIn("--task-identity", help_result.stdout)
        self.assertIn("task_request", help_result.stdout)

        project_root.mkdir(parents=True, exist_ok=True)
        start_result = subprocess.run(
            [
                str(synrail_bin),
                "start",
                "install smoke",
            ],
            check=True,
            cwd=project_root,
            capture_output=True,
            text=True,
        )

        self.assertIn("Controlled run started.", start_result.stdout)
        self.assertIn(
            "Do this now: make the bounded change, run local verification, then strengthen final_result.json first.",
            start_result.stdout,
        )
        self.assertIn("Starter proof surface is ready for this run.", start_result.stdout)
        self.assertIn("Artifact root: .synrail", start_result.stdout)
        self.assertIn("fallback note: readback.txt and scenario_proof.txt stay hidden by default unless a later synrail check names one.", start_result.stdout)
        self.assertIn("Need a canonical final_result shape? run synrail final-result-template", start_result.stdout)
        self.assertIn("Then run: synrail check", start_result.stdout)
        self.assertTrue((artifact_root / "state.json").exists())
        self.assertTrue((artifact_root / "acceptance_criteria.json").exists())
        self.assertTrue((artifact_root / "project_profile.json").exists())
        self.assertTrue((artifact_root / "bootstrap.json").exists())
        self.assertTrue((artifact_root / "proof_request.json").exists())
        self.assertTrue((artifact_root / "final_result.json").exists())
        self.assertFalse((artifact_root / "readback.txt").exists())
        self.assertFalse((artifact_root / "scenario_proof.txt").exists())
        self.assertTrue((artifact_root / "target_identity.txt").exists())
        self.assertTrue((artifact_root / "task_identity.txt").exists())
        self.assertTrue((artifact_root / "prompt_identity.txt").exists())

    def test_supported_installer_boots_synrail_start(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_install_smoke_") as tmpdir:
            root = Path(tmpdir)
            venv_dir = root / "venv"
            project_root = root / "project"

            subprocess.run(
                ["python3", str(INSTALLER), "--venv", str(venv_dir)],
                check=True,
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            self._assert_installed_start_path(
                venv_dir / "bin" / "synrail",
                project_root,
            )

    def test_supported_installer_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_editable_install_smoke_") as tmpdir:
            root = Path(tmpdir)
            venv_dir = root / "venv"
            project_root = root / "project"

            subprocess.run(
                ["python3", str(INSTALLER), "--venv", str(venv_dir)],
                check=True,
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["python3", str(INSTALLER), "--venv", str(venv_dir)],
                check=True,
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            self._assert_installed_start_path(
                venv_dir / "bin" / "synrail",
                project_root,
            )

    def test_supported_installer_can_install_agent_files_into_project(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_install_agent_files_smoke_") as tmpdir:
            root = Path(tmpdir)
            venv_dir = root / "venv"
            project_root = root / "project"
            project_root.mkdir(parents=True, exist_ok=True)
            (project_root / "alpha.py").write_text("print('stub')\n")
            (project_root / "GEMINI.md").write_text("# Existing Gemini Context\n\nKeep this repo focused.\n")

            result = subprocess.run(
                [
                    "python3",
                    str(INSTALLER),
                    "--venv",
                    str(venv_dir),
                    "--project-root",
                    str(project_root),
                ],
                check=True,
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertIn("Agent adoption files are ready.", result.stdout)
            self.assertIn("Agent files installed into:", result.stdout)
            self.assertIn("Git preflight:", result.stdout)
            self.assertIn("No-git proof path: leave git_diff empty and use structured provenance", result.stdout)
            self.assertIn("diff_provenance_records/per_file_diff_provenance", result.stdout)
            self.assertIn("Quick status: run `", result.stdout)
            self.assertIn("inside your project.", result.stdout)
            self.assertIn("Command:", result.stdout)
            self.assertIn('Start a run: `', result.stdout)
            self.assertIn(' start "Describe the bounded local change."`', result.stdout)
            self.assertIn("Repo-native status: `python3 alpha.py`", result.stdout)
            self.assertIn('Repo-native start: `python3 alpha.py start "Describe the bounded local change."`', result.stdout)
            self.assertIn("Repo-native check: `python3 alpha.py check`", result.stdout)
            self.assertIn("Repo-native runtime helper: `python3 alpha.py runtime-helper`", result.stdout)
            self.assertTrue((project_root / "AGENTS.md").exists())
            self.assertTrue((project_root / "CLAUDE.md").exists())
            gemini = (project_root / "GEMINI.md").read_text()
            claude = (project_root / "CLAUDE.md").read_text()
            self.assertIn("# Existing Gemini Context", gemini)
            self.assertIn("<!-- SYNRAIL_GEMINI_START -->", gemini)
            self.assertIn("Use Synrail as the default local control path", gemini)
            self.assertIn("cheapest honest order", gemini)
            self.assertIn("If `git` is unavailable on this host, do not invent `git_diff`", gemini)
            self.assertIn("Do not create helper scripts or make edits for an orientation-only question.", gemini)
            self.assertIn("Do not turn project recall into repo archaeology.", gemini)
            self.assertIn("Use Synrail as the default local control path", claude)
            self.assertIn("cheapest honest order", claude)
            self.assertIn("If `git` is unavailable on this host, do not invent `git_diff`", claude)
            self.assertIn("Do not create helper scripts or make edits for an orientation-only question.", claude)

    def test_first_run_guide_mentions_preflight_and_git_missing_path(self) -> None:
        first_run_guide = (REPO_ROOT / "docs" / "core" / "FIRST_RUN_GUIDE.md").read_text()
        public_readme = (REPO_ROOT / "README.md").read_text()
        docs_readme = (REPO_ROOT / "docs" / "README.md").read_text()
        review_readme = (REPO_ROOT / "docs" / "review" / "README.md").read_text()
        reference_readme = (REPO_ROOT / "tools" / "reference" / "README.md").read_text()
        alpha_lane = (REPO_ROOT / "docs" / "core" / "ALPHA_LANE_001.md").read_text()
        alpha_test_pack = (REPO_ROOT / "docs" / "core" / "ALPHA_TEST_PACK_001.md").read_text()
        external_critique_pack = (REPO_ROOT / "docs" / "review" / "EXTERNAL_CRITIQUE_PACK_001.md").read_text()
        review_handoff_checklist = (REPO_ROOT / "docs" / "review" / "REVIEW_HANDOFF_CHECKLIST_001.md").read_text()

        self.assertIn("Agent: tests passed", first_run_guide)
        self.assertIn("Synrail: Status: Proof Invalid", first_run_guide)
        self.assertIn("Reason: verification command not executed / freshness mismatch", first_run_guide)
        self.assertIn("Next: repair final_result.json", first_run_guide)
        self.assertIn("Only `Status: Accepted` means the task may be reported as complete.", first_run_guide)
        self.assertIn("make install-dev", first_run_guide)
        self.assertIn("make install-local", first_run_guide)
        self.assertIn("This creates the local development venv and installs the `synrail` console script used by the public quickstart.", first_run_guide)
        self.assertIn("On the normal happy path, treat it as the only proof surface you need to touch.", first_run_guide)
        self.assertIn("leave `readback.txt` untouched unless `synrail check` explicitly names it", first_run_guide)
        self.assertIn("leave `scenario_proof.txt` untouched unless `synrail check` explicitly names it", first_run_guide)
        self.assertIn("Only if `check` later targets a fallback prose surface, use:", first_run_guide)
        self.assertIn("Git Preflight", first_run_guide)
        self.assertIn("synrail preflight", first_run_guide)
        self.assertIn("python3 alpha.py preflight", first_run_guide)
        self.assertIn("Git is not installed. Synrail can still use structured diff_provenance, but git_diff and restore coverage will be weaker. Install git for the normal path.", first_run_guide)
        self.assertIn("If `git` is missing, Synrail can still run. Do not invent a `git_diff`.", first_run_guide)
        self.assertIn("leave `git_diff` empty and use structured provenance instead", first_run_guide)
        self.assertIn("for a multi-file change, use `diff_provenance_records` or `per_file_diff_provenance`", first_run_guide)
        self.assertIn('python3 alpha.py start "Describe the bounded local change."', first_run_guide)
        self.assertIn("python3 alpha.py check", first_run_guide)
        self.assertIn("Repeat until `synrail check` prints `Status: Accepted`.", first_run_guide)
        self.assertIn("`Status: Accepted` means the proof bundle is complete", first_run_guide)
        self.assertIn("`Proof Too Thin To Trust` -- structure is there but evidence is thin.", first_run_guide)
        self.assertIn("`Cannot Continue This Run` -- this run reached a terminal rejected state.", first_run_guide)

        self.assertIn("Synrail catches false-green AI-agent work before you accept it.", public_readme)
        self.assertIn("[![CI](https://github.com/USBVadik/synrail/actions/workflows/security-hygiene.yml/badge.svg)]", public_readme)
        self.assertIn("[![License: Apache-2.0]", public_readme)
        self.assertIn("![Python 3.11+]", public_readme)
        self.assertIn("![Status: Alpha]", public_readme)
        self.assertIn("Your coding agent says the task is done.", public_readme)
        self.assertIn("Synrail checks whether the proof is real.", public_readme)
        self.assertIn('The failure mode is simple: an agent says "done", the tests look plausible, and the operator is still missing trustworthy proof.', public_readme)
        self.assertIn("Synrail exists to hold that line between execution and acceptance.", public_readme)
        self.assertIn("## 30-Second Demo", public_readme)
        self.assertIn("Agent: done, tests passed", public_readme)
        self.assertIn("Synrail: Status: Proof Invalid", public_readme)
        self.assertIn("Synrail: Status: Accepted", public_readme)
        self.assertIn("![Synrail false-green demo](examples/false-green-demo/assets/synrail-false-green-hero.gif)", public_readme)
        self.assertIn("[MP4 demo asset](examples/false-green-demo/assets/synrail-false-green-hero.mp4)", public_readme)
        self.assertIn("A simulated false-green claim is blocked until the proof is repaired and verified.", public_readme)
        self.assertIn("[false-green demo](examples/false-green-demo/README.md)", public_readme)
        self.assertIn("[first tester protocol](docs/review/FIRST_TESTER_PROTOCOL_001.md)", public_readme)
        self.assertIn("If you only open three public surfaces, use them in this order:", public_readme)
        self.assertIn("[Your First Synrail Run](docs/core/FIRST_RUN_GUIDE.md)", public_readme)
        self.assertIn("The point is not to make agent output sound confident. The point is to stop false-green closure before it gets accepted as truth.", public_readme)
        self.assertIn("## Is This Just Post-Review?", public_readme)
        self.assertIn("A normal post-review asks: is this code good?", public_readme)
        self.assertIn("Synrail asks a narrower question first: is the agent allowed to claim this task is done?", public_readme)
        self.assertIn("If you personally inspect every diff, run every check, and keep the whole agent context in your head, Synrail may be unnecessary overhead.", public_readme)
        self.assertIn("you are acting as Synrail manually", public_readme)
        self.assertIn("Synrail is for the moment you stop being the runtime supervisor", public_readme)
        self.assertIn("It does not replace review. It prevents unearned acceptance before review.", public_readme)
        self.assertIn("## Try It In 2 Minutes", public_readme)
        self.assertIn("git clone https://github.com/USBVadik/synrail", public_readme)
        self.assertIn("make demo", public_readme)
        self.assertIn("This is the fastest way to see Synrail block a simulated false-green claim and then accept the repaired proof.", public_readme)
        self.assertIn("## Verify The Local Install", public_readme)
        self.assertIn("Use this when you already have the checkout and want the shortest local smoke path.", public_readme)
        self.assertIn("## You May Not Need Synrail If", public_readme)
        self.assertIn("you personally inspect every changed line", public_readme)
        self.assertIn("a false-green costs less than running the gate", public_readme)
        self.assertIn("In that case, the baseline is probably better. Synrail becomes useful when verification debt compounds.", public_readme)
        self.assertIn("## Who This Is For", public_readme)
        self.assertIn("developers using Claude Code, Cursor, Codex, Aider, Gemini CLI, or similar coding agents", public_readme)
        self.assertIn("operators who still manually verify whether an agent's \"done\" claim is actually supported", public_readme)
        self.assertIn("## False-Green Cases Synrail Targets", public_readme)
        self.assertIn("tests claimed as passed but not actually run", public_readme)
        self.assertIn("narrative completion instead of concrete runtime evidence", public_readme)
        self.assertIn("# after make install-dev", public_readme)
        self.assertIn('.venv/bin/synrail start "Describe the bounded local change."', public_readme)
        self.assertIn(".venv/bin/synrail check", public_readme)
        self.assertIn("## Alpha Tester Install Path", public_readme)
        self.assertIn("Use this only when you want the repo-native installer path used by alpha testers.", public_readme)
        self.assertIn("It writes `CLAUDE.md`, `GEMINI.md`, and `AGENTS.md` for agent discovery in the target project.", public_readme)
        self.assertNotIn("python3 tools/reference/synrail_install_v0.py --venv .venv --project-root", public_readme)
        self.assertIn("## Give Feedback", public_readme)
        self.assertIn("Open a `False-green case` issue.", public_readme)
        self.assertIn("Open a `Confusing output` issue.", public_readme)
        self.assertIn("Open an `Alpha feedback` issue.", public_readme)
        self.assertIn("## Comparison Table", public_readme)
        self.assertIn("| Scenario | Manual checks | Agent rules | CI alone | Synrail |", public_readme)
        self.assertIn("Agent claims tests passed but never ran them", public_readme)
        self.assertIn("blocks acceptance until verified", public_readme)
        self.assertIn("names the exact proof repair", public_readme)
        self.assertIn("bounded continuation from artifacts", public_readme)
        self.assertIn("proof gate per run", public_readme)
        self.assertIn("## When To Use It", public_readme)
        self.assertIn("one local agent run on the same machine needs a reviewable proof boundary", public_readme)
        self.assertIn("## When Not To Use It", public_readme)
        self.assertIn("you need a broad self-serve workflow platform or general automation engine", public_readme)
        self.assertIn("you want the current alpha to stand in for full deployment or ops orchestration", public_readme)
        self.assertIn("narrow local alpha product", public_readme)
        self.assertIn("not yet broad self-serve or broad production-ready", public_readme)
        self.assertIn("[Docs Map](docs/README.md)", public_readme)
        self.assertIn("[Review archive map](docs/review/README.md)", public_readme)

        self.assertIn("This is the short current source-of-truth reading path for the repo.", docs_readme)
        self.assertIn("core/FIRST_RUN_GUIDE.md", docs_readme)
        self.assertIn("core/SYNRAIL_RUNTIME_TRUTH_SURFACE.md", docs_readme)
        self.assertIn("Use `docs/review/README.md` only after this map", docs_readme)
        self.assertIn("This index is for deeper review, critique, and outreach material.", review_readme)
        self.assertIn("It is not the primary public source-of-truth reading path for the repo.", review_readme)
        self.assertIn("Current public-proof surfaces on this branch:", review_readme)

        current_public_docs = {
            "README.md": public_readme,
            "docs/core/FIRST_RUN_GUIDE.md": first_run_guide,
            "docs/core/ALPHA_LANE_001.md": alpha_lane,
            "docs/core/ALPHA_TEST_PACK_001.md": alpha_test_pack,
            "docs/review/EXTERNAL_CRITIQUE_PACK_001.md": external_critique_pack,
            "docs/review/REVIEW_HANDOFF_CHECKLIST_001.md": review_handoff_checklist,
            "tools/reference/README.md": reference_readme,
        }
        for name, content in current_public_docs.items():
            with self.subTest(current_public_doc=name):
                self.assertNotIn("python3 tools/reference/synrail_install_v0.py --venv .venv", content)
                self.assertNotIn("python3 tools/reference/synrail_install_v0.py", content)
        self.assertIn("../../examples/false-green-demo/README.md", review_readme)
        self.assertIn("PUBLIC_LAUNCH_PACKET_001.md", review_readme)
        self.assertIn("FIRST_TESTER_PROTOCOL_001.md", review_readme)
        self.assertIn("SERVER_GEMINI_ALPHA_FINDING_001.md", review_readme)

        demo_readme = (REPO_ROOT / "examples" / "false_green_demo.md").read_text()
        demo_pack_readme = (REPO_ROOT / "examples" / "false-green-demo" / "README.md").read_text()
        demo_script = (REPO_ROOT / "examples" / "false-green-demo" / "run_demo.sh").read_text()
        demo_transcript = (REPO_ROOT / "examples" / "false-green-demo" / "transcript.txt").read_text()
        demo_assets_root = REPO_ROOT / "examples" / "false-green-demo" / "assets"
        benchmark_readme = (REPO_ROOT / "examples" / "false-green-benchmark" / "README.md").read_text()
        benchmark_cases = (REPO_ROOT / "examples" / "false-green-benchmark" / "cases.csv").read_text()
        deploy_guard_readme = (REPO_ROOT / "examples" / "deploy_guard" / "README.md").read_text()
        examples_index = (REPO_ROOT / "examples" / "README.md").read_text()
        bug_template = (REPO_ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.md").read_text()
        feature_template = (REPO_ROOT / ".github" / "ISSUE_TEMPLATE" / "feature_request.md").read_text()
        false_green_template = (REPO_ROOT / ".github" / "ISSUE_TEMPLATE" / "false_green_case.yml").read_text()
        confusing_output_template = (REPO_ROOT / ".github" / "ISSUE_TEMPLATE" / "confusing_output.yml").read_text()
        alpha_feedback_template = (REPO_ROOT / ".github" / "ISSUE_TEMPLATE" / "alpha_feedback.yml").read_text()
        launch_packet = (REPO_ROOT / "docs" / "review" / "PUBLIC_LAUNCH_PACKET_001.md").read_text()
        first_tester_protocol = (REPO_ROOT / "docs" / "review" / "FIRST_TESTER_PROTOCOL_001.md").read_text()
        server_gemini_finding = (REPO_ROOT / "docs" / "review" / "SERVER_GEMINI_ALPHA_FINDING_001.md").read_text()
        roadmap_status = (REPO_ROOT / "docs" / "review" / "ROADMAP_STATUS_001.md").read_text()
        contributing = (REPO_ROOT / "CONTRIBUTING.md").read_text()
        security = (REPO_ROOT / "SECURITY.md").read_text()
        pull_request_template = (REPO_ROOT / ".github" / "pull_request_template.md").read_text()
        self.assertIn("# False-Green Demo", demo_readme)
        self.assertIn("Next: repair final_result.json", demo_readme)
        self.assertIn("Synrail: Status: Accepted", demo_readme)
        self.assertIn("only `Status: Accepted` closes the loop", demo_readme)
        self.assertIn("FIRST_TESTER_PROTOCOL_001.md", demo_readme)
        self.assertIn("GitHub issue templates", demo_readme)
        self.assertIn("# False-Green Demo", demo_pack_readme)
        self.assertIn("Run it in under two minutes", demo_pack_readme)
        self.assertIn("1. weak proof attempt gets blocked", demo_pack_readme)
        self.assertIn("2. bounded repair names the next move", demo_pack_readme)
        self.assertIn("3. accepted closure appears only after real verification", demo_pack_readme)
        self.assertIn("./run_demo.sh", demo_pack_readme)
        self.assertIn("assets/synrail-false-green-hero.gif", demo_pack_readme)
        self.assertIn("assets/synrail-false-green-hero.mp4", demo_pack_readme)
        self.assertIn("assets/synrail-false-green-hero-poster.png", demo_pack_readme)
        self.assertTrue((demo_assets_root / "synrail-false-green-hero.gif").is_file())
        self.assertTrue((demo_assets_root / "synrail-false-green-hero.mp4").is_file())
        self.assertTrue((demo_assets_root / "synrail-false-green-hero-poster.png").is_file())
        self.assertIn("FIRST_TESTER_PROTOCOL_001.md", demo_pack_readme)
        self.assertIn("GitHub issue templates", demo_pack_readme)
        self.assertIn("python3 alpha.py check", demo_script)
        self.assertIn("Synrail: Status: Proof Invalid", demo_transcript)
        self.assertIn("Synrail: Status: Accepted", demo_transcript)
        self.assertIn("false-green-demo/", examples_index)
        self.assertIn("false-green-benchmark/", examples_index)
        self.assertIn("`false_green_demo.md`", examples_index)
        self.assertIn("FIRST_TESTER_PROTOCOL_001.md", examples_index)
        self.assertIn("GitHub issue templates", examples_index)
        self.assertIn("# False-Green Benchmark Starter", benchmark_readme)
        self.assertIn("curated local starter scaffold", benchmark_readme)
        self.assertIn("## How to use it", benchmark_readme)
        self.assertIn("## How to read the result labels", benchmark_readme)
        self.assertIn("`repair-needed` means the contour exposed useful signal", benchmark_readme)
        self.assertIn("not measured external rates", benchmark_readme)
        self.assertIn("FIRST_TESTER_PROTOCOL_001.md", benchmark_readme)
        self.assertIn("GitHub issue templates", benchmark_readme)
        self.assertIn("# Deploy Guard Examples", deploy_guard_readme)
        self.assertIn("FIRST_TESTER_PROTOCOL_001.md", deploy_guard_readme)
        self.assertIn("GitHub issue templates", deploy_guard_readme)
        self.assertIn("Case family,Agent claim,Reality,Synrail result,Manual effort,Overhead notes", benchmark_cases)
        self.assertIn("Partial catch,\"done\",\"one issue caught, another still implied safe\",\"repair-needed\"", benchmark_cases)
        self.assertIn("name: Bug report", bug_template)
        self.assertIn("synrail bug-packet --artifact-root .synrail", bug_template)
        self.assertIn("current local alpha lane", bug_template)
        self.assertIn("name: Feature request", feature_template)
        self.assertIn("belongs in Synrail itself", feature_template)
        self.assertIn("current proof-first local alpha lane", feature_template)
        self.assertIn("name: False-green case", false_green_template)
        self.assertIn("Did Synrail catch it?", false_green_template)
        self.assertIn("name: Confusing output", confusing_output_template)
        self.assertIn("Which output was confusing?", confusing_output_template)
        self.assertIn("name: Alpha feedback", alpha_feedback_template)
        self.assertIn("Would you use it again?", alpha_feedback_template)
        self.assertIn("## Issue guidance", contributing)
        self.assertIn("Use the GitHub issue templates to keep bug reports and feature requests bounded.", contributing)
        self.assertIn("## Change Category", pull_request_template)
        self.assertIn("## Risk Surface", pull_request_template)
        self.assertIn("## Split / Scope Check", pull_request_template)
        self.assertIn("- [ ] trust/kernel", pull_request_template)
        self.assertIn("- [ ] This change is small enough to review.", pull_request_template)
        self.assertIn("# Security Policy", security)
        self.assertIn("Please open a GitHub bug report only for issues that belong in Synrail itself.", security)
        self.assertIn("synrail bug-packet --artifact-root .synrail", security)
        self.assertIn("current local alpha support boundary", security)
        self.assertIn("# Public Launch Packet 001", launch_packet)
        self.assertIn("## Twitter/X thread", launch_packet)
        self.assertIn("## LinkedIn post", launch_packet)
        self.assertIn("## GitHub / HN launch blurb", launch_packet)
        self.assertIn("## First tester protocol", launch_packet)
        self.assertIn("Use `FIRST_TESTER_PROTOCOL_001.md` as the shareable one-page handoff.", launch_packet)
        self.assertIn("Read the repo README first screen.", launch_packet)
        self.assertIn("Try one real small local task.", launch_packet)
        self.assertIn("narrow local alpha signal, not broad product readiness proof", launch_packet)
        self.assertIn("## Public-signal freeze rule", roadmap_status)
        self.assertIn("During the current public-signal period, only these changes should land:", roadmap_status)
        self.assertIn("- install-path fixes", roadmap_status)
        self.assertIn("- kernel growth", roadmap_status)
        self.assertIn("# First Tester Protocol 001", first_tester_protocol)
        self.assertIn("Use the GitHub issue templates:", first_tester_protocol)
        self.assertIn("False-green case", first_tester_protocol)
        self.assertIn("# Server Gemini Alpha Finding 001", server_gemini_finding)
        self.assertIn("PATH_SCOPE_VIOLATION", server_gemini_finding)
        self.assertIn("This is a useful alpha integration finding, not a clean success case.", server_gemini_finding)
        self.assertIn("/root/docs/review/SERVER_GEMINI_ALPHA_FINDING_001.md", server_gemini_finding)

        self.assertIn("strengthen final_result.json first", reference_readme)
        self.assertIn("leave readback/scenario_proof untouched unless synrail check later names them", reference_readme)
        self.assertIn("focus on `final_result.json`: status, changed files, and diff/provenance first", reference_readme)


if __name__ == "__main__":
    unittest.main()
