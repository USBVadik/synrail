#!/usr/bin/env python3
"""Fresh unseen validation pack for scoped proof heuristics."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = REPO_ROOT / "tools" / "reference"

if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from synrail_bundle_v0 import (  # noqa: E402
    observation_guard_profile,
    readback_is_semantically_sufficient,
    scenario_is_semantically_sufficient,
    verification_corroboration_is_semantically_sufficient,
)


class FreshUnseenValidationPackTests(unittest.TestCase):
    """Pressure-test current proof guards on fresh task shapes, not only learned probes."""

    def test_strict_readback_accepts_concrete_css_evidence_on_fresh_task(self) -> None:
        self.assertEqual("STRICT_RUNTIME_EVIDENCE", observation_guard_profile("proof_sensitive_style_tweak"))
        self.assertTrue(readback_is_semantically_sufficient(
            'Changed surface: web/banner.css\n'
            'Observed: web/banner.css line 14 now reads ".hero-note { letter-spacing: 0.08em; }".',
            ["web/banner.css"],
            task_identity="add a small tracking adjustment to the hero note in web/banner.css",
            task_class="proof_sensitive_style_tweak",
        ))

    def test_strict_readback_accepts_concrete_html_copy_evidence_on_fresh_task(self) -> None:
        self.assertEqual("STRICT_RUNTIME_EVIDENCE", observation_guard_profile("proof_sensitive_copy_update"))
        self.assertTrue(readback_is_semantically_sufficient(
            'Changed surface: templates/home.html\n'
            'Observed: templates/home.html line 28 now shows "Ships in 48 hours" inside the support badge.',
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))

    def test_strict_readback_rejects_fresh_narrative_without_evidence(self) -> None:
        self.assertEqual("STRICT_RUNTIME_EVIDENCE", observation_guard_profile("proof_sensitive_router_adjustment"))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: services/router.py\n"
            "Observed: the retry guard was updated correctly in the router module.",
            ["services/router.py"],
            task_identity="tighten the retry guard in services/router.py",
            task_class="proof_sensitive_router_adjustment",
        ))

    def test_strict_readback_rejects_domain_specific_thin_claim_on_fresh_task(self) -> None:
        self.assertEqual("STRICT_RUNTIME_EVIDENCE", observation_guard_profile("proof_sensitive_billing_adjustment"))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: services/billing_rules.py\n"
            "Observed: services/billing_rules.py now applies the merchant grace-period clamp before surcharge evaluation.",
            ["services/billing_rules.py"],
            task_identity="tighten merchant grace-period clamp before surcharge evaluation",
            task_class="proof_sensitive_billing_adjustment",
        ))

    def test_strict_readback_rejects_structured_but_thin_self_description_on_fresh_task(self) -> None:
        self.assertEqual("STRICT_RUNTIME_EVIDENCE", observation_guard_profile("proof_sensitive_billing_adjustment"))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: services/billing_rules.py\n"
            "Observed: services/billing_rules.py contains a merchant grace-period clamp before surcharge evaluation.",
            ["services/billing_rules.py"],
            task_identity="tighten merchant grace-period clamp before surcharge evaluation",
            task_class="proof_sensitive_billing_adjustment",
        ))

    def test_strict_readback_rejects_thin_line_location_claim_on_fresh_task(self) -> None:
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: shipping note is at line 28 inside the support badge.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))

    def test_strict_readback_rejects_line_numbered_paraphrase_on_fresh_task(self) -> None:
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 updates the support badge shipping note.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28: updates the support badge shipping note.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 shows the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 mentions the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 indicates the support badge shipping note was updated.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 confirms the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 notes the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 reports the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 records the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 documents the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 describes the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 reflects the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 captures the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 lists the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 presents the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 carries the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 marks the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 preserves the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 maintains the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 keeps the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 sets the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 includes the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 displays the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 renders the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 holds the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 stores the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 moves the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 places the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 puts the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 leaves the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 states the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 spells the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 features the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 offers the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 delivers the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 serves the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 surfaces the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 exposes the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 hosts the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 announces the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 signals the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 conveys the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 relays the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 reveals the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 highlights the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 spotlights the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 showcases the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: templates/home.html\n"
            "Observed: templates/home.html line 28 underlines the support badge shipping note update.",
            ["templates/home.html"],
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))

    def test_strict_scenario_accepts_real_command_output_on_fresh_task(self) -> None:
        self.assertTrue(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: 28:        <span class=\"support-badge\">Ships in 48 hours</span>\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))

    def test_strict_scenario_accepts_real_result_output_on_fresh_task(self) -> None:
        self.assertTrue(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Result: 28:        <span class=\"support-badge\">Ships in 48 hours</span>\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertTrue(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Output: 28:        <span class=\"support-badge\">Ships in 48 hours</span>\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))

    def test_strict_scenario_rejects_assertion_only_on_fresh_task(self) -> None:
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify retry guard in services/router.py\n"
            "Command: rg -n \"retry_guard\" services/router.py\n"
            "Observed: retry guard added to services/router.py\n"
            "Result: retry guard is present in services/router.py\n"
            "Status: PASSED",
            task_identity="tighten the retry guard in services/router.py",
            task_class="proof_sensitive_router_adjustment",
        ))

    def test_strict_scenario_rejects_thin_line_location_claim_on_fresh_task(self) -> None:
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: shipping note is at line 28 inside the support badge\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))

    def test_strict_scenario_rejects_line_numbered_paraphrase_on_fresh_task(self) -> None:
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: line 28 updates the support badge shipping note\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: line 28: updates the support badge shipping note\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: line 28 shows the support badge shipping note update\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: templates/home.html line 28 documents the support badge shipping note update.\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: templates/home.html line 28 describes the support badge shipping note update.\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: templates/home.html line 28 reflects the support badge shipping note update.\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: templates/home.html line 28 captures the support badge shipping note update.\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: templates/home.html line 28 lists the support badge shipping note update.\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: templates/home.html line 28 presents the support badge shipping note update.\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: templates/home.html line 28 carries the support badge shipping note update.\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: templates/home.html line 28 marks the support badge shipping note update.\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: templates/home.html line 28 preserves the support badge shipping note update.\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: templates/home.html line 28 maintains the support badge shipping note update.\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: templates/home.html line 28 keeps the support badge shipping note update.\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: templates/home.html line 28 sets the support badge shipping note update.\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: templates/home.html line 28 includes the support badge shipping note update.\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: templates/home.html line 28 displays the support badge shipping note update.\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: templates/home.html line 28 renders the support badge shipping note update.\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: templates/home.html line 28 holds the support badge shipping note update.\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: templates/home.html line 28 stores the support badge shipping note update.\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: templates/home.html line 28 moves the support badge shipping note update.\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: templates/home.html line 28 places the support badge shipping note update.\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: templates/home.html line 28 puts the support badge shipping note update.\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: templates/home.html line 28 leaves the support badge shipping note update.\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: templates/home.html line 28 states the support badge shipping note update.\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: templates/home.html line 28 spells the support badge shipping note update.\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: templates/home.html line 28 features the support badge shipping note update.\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: templates/home.html line 28 offers the support badge shipping note update.\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: templates/home.html line 28 delivers the support badge shipping note update.\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: templates/home.html line 28 serves the support badge shipping note update.\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: templates/home.html line 28 surfaces the support badge shipping note update.\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: templates/home.html line 28 exposes the support badge shipping note update.\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: templates/home.html line 28 hosts the support badge shipping note update.\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: templates/home.html line 28 announces the support badge shipping note update.\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: templates/home.html line 28 signals the support badge shipping note update.\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: templates/home.html line 28 conveys the support badge shipping note update.\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: templates/home.html line 28 relays the support badge shipping note update.\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: templates/home.html line 28 reveals the support badge shipping note update.\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: templates/home.html line 28 highlights the support badge shipping note update.\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: templates/home.html line 28 spotlights the support badge shipping note update.\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: templates/home.html line 28 showcases the support badge shipping note update.\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify shipping note in support badge\n"
            "Command: rg -n \"Ships in 48 hours\" templates/home.html\n"
            "Observed: templates/home.html line 28 underlines the support badge shipping note update.\n"
            "Status: PASSED",
            task_identity="append a small shipping note inside the support badge",
            task_class="proof_sensitive_copy_update",
        ))

    def test_strict_scenario_rejects_structured_but_thin_self_description_on_fresh_task(self) -> None:
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify retry guard in services/router.py\n"
            "Command: rg -n \"retry_guard\" services/router.py\n"
            "Observed: services/router.py contains a retry guard before dispatch.\n"
            "Status: PASSED",
            task_identity="tighten the retry guard in services/router.py",
            task_class="proof_sensitive_router_adjustment",
        ))

    def test_strict_scenario_rejects_domain_specific_thin_observed_on_fresh_task(self) -> None:
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify billing clamp in services/billing_rules.py\n"
            "Command: rg -n \"grace-period|surcharge\" services/billing_rules.py\n"
            "Observed: services/billing_rules.py applies the merchant grace-period clamp before surcharge evaluation.\n"
            "Status: PASSED",
            task_identity="tighten merchant grace-period clamp before surcharge evaluation",
            task_class="proof_sensitive_billing_adjustment",
        ))

    def test_strict_scenario_rejects_domain_specific_thin_result_on_fresh_task(self) -> None:
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify billing clamp in services/billing_rules.py\n"
            "Command: rg -n \"grace-period|surcharge\" services/billing_rules.py\n"
            "Result: services/billing_rules.py applies the merchant grace-period clamp before surcharge evaluation.\n"
            "Status: PASSED",
            task_identity="tighten merchant grace-period clamp before surcharge evaluation",
            task_class="proof_sensitive_billing_adjustment",
        ))

    def test_strict_scenario_rejects_domain_specific_thin_output_on_fresh_task(self) -> None:
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify billing clamp in services/billing_rules.py\n"
            "Command: rg -n \"grace-period|surcharge\" services/billing_rules.py\n"
            "Output: services/billing_rules.py applies the merchant grace-period clamp before surcharge evaluation.\n"
            "Status: PASSED",
            task_identity="tighten merchant grace-period clamp before surcharge evaluation",
            task_class="proof_sensitive_billing_adjustment",
        ))

    def test_strict_scenario_rejects_structured_but_thin_result_self_description_on_fresh_task(self) -> None:
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify retry guard in services/router.py\n"
            "Command: rg -n \"retry_guard\" services/router.py\n"
            "Result: services/router.py contains a retry guard before dispatch.\n"
            "Status: PASSED",
            task_identity="tighten the retry guard in services/router.py",
            task_class="proof_sensitive_router_adjustment",
        ))

    def test_strict_scenario_rejects_structured_but_thin_output_self_description_on_fresh_task(self) -> None:
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify retry guard in services/router.py\n"
            "Command: rg -n \"retry_guard\" services/router.py\n"
            "Output: services/router.py contains a retry guard before dispatch.\n"
            "Status: PASSED",
            task_identity="tighten the retry guard in services/router.py",
            task_class="proof_sensitive_router_adjustment",
        ))

    def test_runtime_backed_corroboration_dominates_prose_on_strict_fresh_task(self) -> None:
        self.assertTrue(verification_corroboration_is_semantically_sufficient(
            runtime_verification_sufficient=True,
            scenario_text=(
                "Scenario: verify retry guard in services/router.py\n"
                "Command: rg -n \"retry_guard\" services/router.py\n"
                "Observed: retry guard added to services/router.py\n"
                "Result: retry guard is present in services/router.py\n"
                "Status: PASSED"
            ),
            task_identity="tighten the retry guard in services/router.py",
            task_class="proof_sensitive_router_adjustment",
        ))

    def test_unknown_task_class_does_not_inherit_strict_guard_on_fresh_task(self) -> None:
        self.assertEqual("BASELINE_OBSERVATION", observation_guard_profile("cross_repo_orientation_probe"))
        self.assertTrue(readback_is_semantically_sufficient(
            "Changed surface: docs/notes.md\n"
            "Observed: release note added to docs/notes.md.",
            ["docs/notes.md"],
            task_identity="add a release note line to docs/notes.md",
            task_class="cross_repo_orientation_probe",
        ))

    def test_unknown_task_class_scenario_stays_followable_without_strict_guard(self) -> None:
        self.assertTrue(scenario_is_semantically_sufficient(
            "Scenario: verify release note in docs/notes.md\n"
            "Command: rg -n \"release note\" docs/notes.md\n"
            "Observed: release note added to docs/notes.md\n"
            "Status: PASSED",
            task_identity="add a release note line to docs/notes.md",
            task_class="cross_repo_orientation_probe",
        ))


if __name__ == "__main__":
    unittest.main()
