from dataclasses import replace
import unittest
from almadar_fabric.agents import Registry, default_registry
from almadar_fabric.audit import verify_chain
from almadar_fabric.models import Order
from almadar_fabric.runtime import run, sample_order


class FulfilmentTests(unittest.TestCase):
    def test_complete_only_after_validation(self):
        result = run()
        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["service_active"])
        tasks = [r["details"]["task"]["skill"] for r in result["audit"] if r["kind"] == "task"]
        self.assertEqual(tasks, ["identity.verify", "access.qualify", "transport.qualify", "service.provision", "service.validate"])
        self.assertTrue(verify_chain(result["audit"]))

    def test_infeasible_orders_never_provision(self):
        for scenario, status in [("identity-rejected", "rejected"), ("access-build", "awaiting-operator"),
                                 ("capacity-shortfall", "awaiting-operator"), ("untrusted-agent", "awaiting-operator")]:
            with self.subTest(scenario=scenario):
                result = run(scenario=scenario)
                self.assertEqual(result["status"], status)
                self.assertFalse(result["service_active"])
                self.assertNotIn("service.provision", result["results"])

    def test_capacity_shortfall_preserves_intent(self):
        result = run(scenario="capacity-shortfall")
        self.assertEqual(result["order"]["bandwidth_mbps"], 200)
        negotiations = [r for r in result["audit"] if r["kind"] == "negotiation"]
        self.assertEqual(negotiations[0]["details"]["offered_bandwidth_mbps"], 100)

    def test_budget_and_latency_gate(self):
        for order in [replace(sample_order(), budget_lyd=1000), replace(sample_order(), max_latency_ms=10)]:
            with self.subTest(order=order):
                result = run(order)
                self.assertEqual(result["status"], "awaiting-operator")
                self.assertFalse(result["service_active"])
                self.assertNotIn("service.provision", result["results"])

    def test_failed_validation_rolls_back(self):
        result = run(scenario="validation-failed")
        self.assertEqual(result["status"], "rolled-back")
        self.assertFalse(result["service_active"])
        self.assertTrue(result["results"]["service.rollback"]["rolled_back"])

    def test_missing_validator_compensates(self):
        cards = [c for c in default_registry().cards if c.agent_id != "assurance"]
        result = run(registry=Registry(cards))
        self.assertEqual(result["status"], "awaiting-operator")
        self.assertFalse(result["service_active"])
        self.assertIn("service.rollback", result["results"])

    def test_missing_rollback_agent_requires_manual_recovery(self):
        cards = [replace(c, skills=("service.provision",)) if c.agent_id == "provision" else c
                 for c in default_registry().cards if c.agent_id != "assurance"]
        result = run(registry=Registry(cards))
        self.assertEqual(result["status"], "manual-recovery")
        self.assertTrue(result["service_active"])
        self.assertNotIn("service.rollback", result["results"])

    def test_discovery_rejects_unonboarded_or_low_trust(self):
        card = default_registry().cards[0]
        for invalid in [replace(card, onboarded=False), replace(card, trust_score=0.1)]:
            with self.assertRaises(LookupError):
                Registry([invalid]).discover("identity.verify")

    def test_audit_detects_mutation_and_reordering(self):
        records = run()["audit"]
        records[2]["summary"] = "tampered"
        self.assertFalse(verify_chain(records))
        records = run()["audit"]
        records[1], records[2] = records[2], records[1]
        self.assertFalse(verify_chain(records))

    def test_task_correlation(self):
        result = run()
        tasks = [r["details"]["task"] for r in result["audit"] if r["kind"] == "task"]
        self.assertEqual({t["context_id"] for t in tasks}, {result["context_id"]})
        self.assertEqual(len({t["task_id"] for t in tasks}), len(tasks))

    def test_order_validation(self):
        for field, value in [("bandwidth_mbps", True), ("budget_lyd", -1), ("max_latency_ms", float("nan")),
                             ("max_latency_ms", float("inf")), ("site", "")]:
            data = vars(sample_order()).copy()
            data[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                Order.from_dict(data)
        with self.assertRaises(ValueError):
            run(scenario="unknown")


if __name__ == "__main__":
    unittest.main()
