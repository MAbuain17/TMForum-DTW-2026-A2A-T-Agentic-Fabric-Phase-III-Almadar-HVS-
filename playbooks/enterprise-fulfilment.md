# Almadar enterprise fulfilment playbook

## Identity

Scenario: enterprise connectivity fulfilment, adapted from Catalyst HVS3.
Operator context: Almadar Aljadid.
Environment: local sandbox with synthetic enterprise and network data.
Intent: activate the requested service only if identity, readiness, capacity, cost and measured performance satisfy the order.

## Agent roster

| Role | Skill | Responsibility |
| --- | --- | --- |
| Service orchestrator | Local process controller | Retain intent and coordinate the fulfilment sequence |
| Identity verifier | `identity.verify` | Confirm enterprise identity |
| Access planner | `access.qualify` | Check circuit, equipment and access readiness |
| Transport planner | `transport.qualify` | Evaluate bandwidth, expected latency and cost |
| Service provisioner | `service.provision`, `service.rollback` | Apply and revert sandbox configuration |
| Service validator | `service.validate` | Test throughput and latency before completion |

## Expected behaviour

Verify the enterprise. Check access readiness. Check transport feasibility. Reject any plan that exceeds budget or latency, or cannot provide the requested bandwidth. Provision only after the prerequisites pass. Confirm the service only after activation tests pass. Record every task, result and terminal decision.

## Governance

Only onboarded agents with trust at or above 0.80 may receive tasks. Discovery must match the requested skill. The operator's bandwidth, latency and budget constraints must accompany each task. This implementation executes no arbitrary command strings and calls no real network equipment.

## Delegation and negotiation

Dispatch structured local Task-T-style records by skill. An access build generates an input-required negotiation record. A capacity shortfall records the available bandwidth as a proposal and preserves the original order. The simulator stops for operator review; it does not accept the proposal on behalf of the customer.

## Human handoff

Require operator intervention for physical construction, infeasible terms, insufficient agent trust, missing capabilities or failed validation. A failed identity check rejects the order before service activity.

## Escalation and recovery

If service validation fails, request rollback through an eligible agent and retain the service ID as evidence of the attempted activation. If an assurance agent cannot be discovered after provisioning, attempt compensation. If compensation cannot be dispatched, report `manual-recovery` with the remaining sandbox service state.

This Markdown describes the process implemented in `runtime.py`; it is not a machine-executed rules engine or a formal TM Forum playbook schema.
