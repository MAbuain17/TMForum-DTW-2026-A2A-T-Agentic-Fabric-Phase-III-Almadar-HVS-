"""Execute the HVS3 operator process with policy gates at every handoff."""

from uuid import uuid4
from .agents import SandboxAdapters, default_registry
from .audit import AuditLog, verify_chain
from .models import Order, Task

SCENARIOS = {
    "ready": "Ready for activation",
    "access-build": "Access circuit requires construction",
    "capacity-shortfall": "Transport capacity below requested bandwidth",
    "identity-rejected": "Enterprise identity cannot be verified",
    "untrusted-agent": "Provisioning agent below the trust threshold",
    "validation-failed": "Post-activation latency exceeds the SLA",
}


def sample_order():
    return Order("ALM-ENT-001", "Demo Enterprise", "Tripoli branch (fictional)", 200, 20, 2000)


def run(order=None, scenario="ready", registry=None, adapters=None):
    if scenario not in SCENARIOS:
        raise ValueError("Unknown scenario")
    order = Order.from_dict(vars(order or sample_order()))
    context = str(uuid4())
    log = AuditLog()
    registry = registry if registry is not None else default_registry(scenario)
    adapters = adapters if adapters is not None else SandboxAdapters(scenario)
    service_id = None
    results = {}
    task_counter = 0

    def dispatch(skill, intent):
        nonlocal task_counter
        task_counter += 1
        try:
            card = registry.discover(skill)
        except LookupError as exc:
            log.append("policy", "governance", str(exc), decision="deny", skill=skill)
            raise
        task = Task(context, f"{context}:{task_counter}", skill, order.site, intent,
                    {"bandwidth_mbps": order.bandwidth_mbps, "max_latency_ms": order.max_latency_ms,
                     "budget_lyd": order.budget_lyd, "simulation_only": True})
        log.append("task", card.agent_id, intent, task=task.to_dict(), provider=card.provider)
        response = adapters.execute(skill, order)
        results[skill] = response
        log.append("result", card.agent_id, f"{card.name} returned evidence", response=response)
        return response

    def finish(status, reason):
        log.append("event", "orchestrator", reason, event="order.status.changed", status=status,
                   context_id=context)
        records = log.records
        return {"context_id": context, "scenario": scenario, "status": status, "reason": reason,
                "order": vars(order), "service_id": service_id, "service_active": adapters.active,
                "results": results, "agents": [c.to_dict() for c in registry.cards],
                "audit": records, "audit_valid": verify_chain(records), "audit_head": records[-1]["hash"]}

    log.append("event", "orchestrator", "Enterprise order accepted", event="order.received", order_id=order.order_id)
    try:
        identity = dispatch("identity.verify", "Verify the enterprise before qualifying service")
        if not identity["verified"]:
            return finish("rejected", "Identity verification failed; no service changes made")
        access = dispatch("access.qualify", "Check access circuit and customer equipment readiness")
        if not access["ready"]:
            log.append("negotiation", "access", "A site survey and access build are required",
                       outcome="input-required", required_input="Operator-approved survey and construction plan")
            return finish("awaiting-operator", "Physical access build required before service provisioning")
        transport = dispatch("transport.qualify", "Check bandwidth, latency and transport cost")
        if min(access["capacity_mbps"], transport["capacity_mbps"]) < order.bandwidth_mbps:
            log.append("negotiation", "transport", "Requested bandwidth is not feasible",
                       outcome="input-required", offered_bandwidth_mbps=transport["capacity_mbps"],
                       requested_bandwidth_mbps=order.bandwidth_mbps)
            return finish("awaiting-operator", "Capacity shortfall; the requested service has not been downgraded")
        cost = access["cost_lyd"] + transport["cost_lyd"]
        if cost > order.budget_lyd or transport["expected_latency_ms"] > order.max_latency_ms:
            log.append("policy", "governance", "Proposed service exceeds the agreed budget or latency",
                       decision="deny", quoted_cost_lyd=cost, expected_latency_ms=transport["expected_latency_ms"])
            return finish("awaiting-operator", "Service proposal requires revised commercial or SLA terms")
        log.append("policy", "governance", "Identity, access, capacity, cost and latency checks passed",
                   decision="allow", quoted_cost_lyd=cost)
        receipt = dispatch("service.provision", "Provision the qualified service in the sandbox")
        service_id = receipt["service_id"]
        validation = dispatch("service.validate", "Measure throughput and latency before confirming activation")
        if validation["throughput_mbps"] < order.bandwidth_mbps or validation["latency_ms"] > order.max_latency_ms:
            dispatch("service.rollback", "Revert sandbox configuration after failed activation checks")
            return finish("rolled-back", "Activation test failed; configuration reverted for operator review")
        return finish("completed", "Service activated after throughput and latency validation")
    except LookupError as exc:
        if adapters.active:
            # Compensate using an authorised provisioner; do not bypass discovery.
            try:
                dispatch("service.rollback", "Revert sandbox configuration after agent discovery failure")
            except LookupError:
                return finish("manual-recovery", "Rollback agent unavailable; sandbox service remains configured")
        return finish("awaiting-operator", str(exc))
