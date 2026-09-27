from copy import deepcopy
from dataclasses import replace
import unittest
from almadar_fabric.audit import verify_chain
from almadar_fabric.models import Incident, DispatchDenied
from almadar_fabric.process import compile_process, render_prompt
from almadar_fabric.runtime import run, AssuranceSession, SCENARIOS


class MobileAssuranceTests(unittest.TestCase):
    def test_mobile_service_restored_after_parallel_join(self):
        result = run()
        self.assertEqual(result["status"], "restored")
        self.assertEqual(
            result["results"]["Task_CEAndImpact"]["affected_subscribers"], 840
        )
        join = next(i for i, r in enumerate(result["audit"]) if r["kind"] == "join")
        executed = {
            r["details"].get("activity")
            for r in result["audit"][:join]
            if r["kind"] == "execute"
        }
        self.assertEqual(executed, {"Task_RCA", "Task_CEAndImpact"})
        self.assertTrue(verify_chain(result["audit"]))

    def test_bpmn_join_requires_both_branches(self):
        design = compile_process()
        self.assertEqual(
            design["templates"]["Task_Prioritize"]["required_evidence"],
            ["Task_CEAndImpact", "Task_RCA"],
        )
        self.assertEqual(len(design["templates"]), 6)
        self.assertEqual(design, compile_process())

    def test_only_transport_changes(self):
        result = run()
        self.assertEqual(
            [x["domain"] for x in result["domain_actions"] if x["changed"]],
            ["Transport"],
        )

    def test_failures_before_remediation_do_not_change_network(self):
        for scenario in (
            "missing-topology",
            "unsafe-action",
            "prompt-tampered",
            "unregistered-agent",
        ):
            with self.subTest(scenario=scenario):
                r = run(scenario=scenario)
                self.assertEqual(r["status"], "awaiting-operator")
                self.assertFalse(r["network_changed"])
                self.assertNotIn("Task_ConfirmRestoration", r["results"])

    def test_failed_verification_keeps_incident_open(self):
        r = run(scenario="persistent-degradation")
        self.assertTrue(r["network_changed"])
        self.assertEqual(r["status"], "escalated")
        self.assertFalse(r["results"]["Task_ConfirmRestoration"]["restored"])

    def test_actual_input_threshold_controls_closure(self):
        r = run(replace(Incident(), min_throughput_mbps=30))
        self.assertEqual(r["status"], "escalated")

    def test_identifiers_redacted_before_receiver(self):
        r = run(scenario="privacy-redaction")
        self.assertEqual(r["status"], "restored")
        self.assertTrue(
            any(e["verdict"] == "REDACT" for e in r["governance"]["events"])
        )
        import json

        self.assertNotIn("synthetic-subscriber-001", json.dumps(r))

    def payload(self):
        session = AssuranceSession(Incident(), "transport-fault")
        template = session.design["templates"]["Task_Prioritize"]
        evidence = {"Task_RCA": {}, "Task_CEAndImpact": {}}
        payload = {
            "initiator": "diagnostics",
            "executor": "prioritise",
            "activity": template["id"],
            "skill": template["skill"],
            "template_hash": template["template_hash"],
            "structured_prompt": render_prompt(template, session.incident, evidence),
            "evidence": evidence,
        }
        return session, template, payload

    def test_missing_join_evidence_is_rejected(self):
        s, t, p = self.payload()
        p["evidence"].pop("Task_CEAndImpact")
        with self.assertRaises(DispatchDenied):
            s.gateway.sign(p, t, s.incident, s.registry)

    def test_wrong_initiator_is_rejected(self):
        s, t, p = self.payload()
        p["initiator"] = "transport"
        with self.assertRaises(DispatchDenied):
            s.gateway.sign(p, t, s.incident, s.registry)

    def test_changed_template_content_is_rejected(self):
        s, t, p = self.payload()
        p["structured_prompt"]["Task Description"] = "Do something else"
        with self.assertRaises(DispatchDenied):
            s.gateway.sign(p, t, s.incident, s.registry)

    def test_target_outside_incident_is_rejected(self):
        s, t, p = self.payload()
        p["structured_prompt"]["Target Object"]["transport_id"] = "OTHER"
        with self.assertRaises(DispatchDenied):
            s.gateway.sign(p, t, s.incident, s.registry)

    def test_receiver_and_replay_validation(self):
        s, t, p = self.payload()
        envelope = s.gateway.sign(p, t, s.incident, s.registry)
        with self.assertRaises(DispatchDenied):
            s.gateway.verify(envelope, "ran")
        s.gateway.verify(envelope, "prioritise")
        with self.assertRaises(DispatchDenied):
            s.gateway.verify(envelope, "prioritise")

    def test_passport_tampering_is_rejected(self):
        s, t, p = self.payload()
        e = s.gateway.sign(p, t, s.incident, s.registry)
        e["passport"]["incident_id"] = "OTHER"
        with self.assertRaises(DispatchDenied):
            s.gateway.verify(e, "prioritise")

    def test_observer_score_does_not_revoke_onboarding(self):
        s, t, p = self.payload()
        for _ in range(10):
            s.observer.observe("prioritise", "BLOCK", "test advisory observation")
        self.assertLess(s.observer.scores["prioritise"], 0)
        e = s.gateway.sign(p, t, s.incident, s.registry)
        s.gateway.verify(e, "prioritise")
        self.assertTrue(s.registry.cards["prioritise"]["onboarded"])

    def test_audit_tamper_is_detected(self):
        r = run()
        records = deepcopy(r["audit"])
        records[2]["summary"] = "altered"
        self.assertFalse(verify_chain(records))

    def test_all_conditions_leave_valid_audit(self):
        for condition in SCENARIOS:
            with self.subTest(condition=condition):
                self.assertTrue(run(scenario=condition)["audit_valid"])

    def test_aggregate_impact_follows_operator_input(self):
        r = run(replace(Incident(), affected_subscribers=123))
        self.assertEqual(r["results"]["Task_CEAndImpact"]["affected_subscribers"], 123)

    def test_invalid_incident_input(self):
        for data in (
            {"affected_subscribers": True},
            {"packet_loss_pct": 101},
            {"throughput_mbps": float("nan")},
            {"cell_ids": ["A", "A"]},
            {"enterprise": True},
        ):
            with self.subTest(data=data):
                with self.assertRaises(ValueError):
                    Incident.from_dict(data)

    def test_unknown_scenario(self):
        with self.assertRaises(ValueError):
            run(scenario="unknown")


if __name__ == "__main__":
    unittest.main()
