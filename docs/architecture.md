# Architecture

The demo separates the operator process from domain-specific execution. The orchestrator decides the next task; the registry selects an eligible agent; the adapter returns a structured result; the audit log records the handoff and evidence. No language model is required to demonstrate these control boundaries.

## Runtime sequence

1. Validate the six-field order contract and assign a new context ID.
2. Discover an onboarded identity agent with trust of at least 0.80.
3. Qualify access readiness and transport feasibility through separate agents.
4. Compare capacity, expected latency and quoted costs with the original intent.
5. Discover an eligible provisioner and configure the sandbox service.
6. Check measured throughput and latency through the assurance adapter.
7. Complete the order, or dispatch a compensating rollback and escalate.

The registry ranks eligible agents by trust score, with agent ID as a stable tie-breaker. The score is a fixture, not a runtime assessment. If no eligible agent exists, the task is denied. Failure to discover the validator after provisioning triggers rollback; failure to find a rollback agent leaves the order in `manual-recovery` and reports that the sandbox remains configured.

## Contracts

Every local task contains a `context_id`, unique `task_id`, skill, target, intent, HVS reference and constraints. The profile name is `almadar-demo/task-t/0.1`. It deliberately uses a local identifier to avoid suggesting that its JSON is the normative A2A-T wire format.

Task results contain specific evidence references such as `synthetic/transport-inventory`. Negotiation records explain an unmet prerequisite or proposed alternative. Event records describe order transitions. All three are plain dictionaries in this demo; there is no event broker or distributed negotiation session.

## Policy and recovery

Policy checks are executed by the orchestrator. Agent selection is enforced by the registry. There is no separate governance service. A physical access build requires operator review because the simulator cannot perform surveys, procurement or construction. An infeasible service is never automatically downgraded.

Rollback is a simulated compensating action. It does not undo real devices, inventory reservations or billing. Adapter exceptions, timeouts, partial provisioning and retry recovery would need explicit handling before connecting external systems.

## Audit boundary

Records include sequence, UTC timestamp, agent identity, structured details and the previous record's SHA-256 hash. Hashing uses canonical JSON. The exported `audit_head` provides an end marker checked by the CLI verifier.

Verification detects edits and ordering errors against the supplied chain and head. It cannot prove authenticity if an attacker replaces the entire export and recalculates the hashes. A production design needs a separately retained signed head, authenticated identities, access-controlled storage and retention policy.

## Integration plan

| Local component | External integration needed |
| --- | --- |
| In-memory registry | OpenAN Registry Center, authenticated registration and capability discovery |
| Python function dispatch | A2A/A2A-T SDK transport with supported profiles and version negotiation |
| Fixed domain responses | Approved CRM, service inventory, transport and assurance adapters |
| Local policy checks | Operator governance service with role and action authorisation |
| Exported JSON audit | Durable evidence store with signing and independent retention |
| Immediate sandbox runs | Persistent task state, idempotency, retries, cancellation and long-running workflows |

The browser server binds only to loopback. It exposes fixed static assets, scenario metadata and a run endpoint. It has no authentication or production deployment mode. Each request creates a new isolated sandbox; orders are not retained or deduplicated. The UI displays the run returned by the Python engine rather than reimplementing the process in JavaScript.
