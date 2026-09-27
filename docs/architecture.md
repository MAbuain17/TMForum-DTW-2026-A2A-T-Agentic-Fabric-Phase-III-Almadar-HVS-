# Architecture

The design-time compiler reads `mobile-assurance.bpmn` and publishes a process graph, per-lane activity lists and version-pinned structured task templates. The six activities preserve the HVS1 analysis fork and join. The supported BPMN subset is intentionally small; it is not an execution engine.

At runtime, the anomaly agent initiates root-cause and subscriber-impact tasks concurrently. The diagnostic agent receives both results and initiates prioritisation. The receiving agent then initiates the next handoff through recommendation, coordination and verification. `AssuranceSession` hosts these local handlers; it is an in-process simulation, not a distributed agent platform. The gateway does not choose the next activity.

Each dispatch discovers a registered capability, renders the operator template, checks required evidence and caller ownership, and passes through the trust boundary. The platform signs an incident-scoped intent hash. The receiving adapter validates the signature, payload, recipient and single-use passport before execution. Sign, verify and execute records share passport identifiers. The signing key is ephemeral and never exported.

## Local profiles

Task-T sections are **Task Description, Task Type, Target Object, Task Context, Constraints, Expected Output**. They are placed in local message metadata alongside evidence and a template hash. These messages illustrate the project’s layering but are not a normative A2A-T wire implementation.

The trust profile uses HMAC-SHA256 inside one process. Production platform attestations require asymmetric signatures, issuer trust, expiry, durable replay protection, receiver authentication and key management. Domain child requests are derived from the coordination template; their local skill slices are not separate activities in the supplied HVS1 BPMN.

Event-T is represented by a domain-scoped anomaly subscription match. Negotiation-T is represented by an incident target and deterministic backup-path feasibility decision before domain execution. Neither is a full subscription service or multi-round negotiation transport.

The governance observer records ALLOW (+0.05), REDACT (−0.01) and BLOCK (−1.05), starting at a configurable-in-code demo baseline of 5.0. Scores are advisory; they do not automatically revoke registration. The gateway independently enforces scope and integrity. This selects the advisory source variant rather than blending incompatible trust-score proposals.

Privacy redaction removes a known synthetic subscriber identifier field before attestation. It is not a general data-loss prevention classifier. Explainability records cite fixture evidence and do not claim calibrated probabilistic confidence. The RAN and core checks are simulated observations; only the transport adapter changes the local network state.

## Restoration and failure handling

No domain action starts until all three domain capabilities are available. Missing topology, unsafe action scope and altered messages halt execution and return `awaiting-operator`. After a simulated transport change, verification uses the input incident’s throughput and packet-loss thresholds. Failed verification returns `escalated`; it does not claim successful closure or a completed rollback.

The server binds to loopback, accepts bounded JSON requests and serves a fixed asset list. Run traces remain in memory unless explicitly exported. Audit records are append-only during a run and hash-linked under a lock so parallel analysis cannot corrupt sequence order. A valid chain does not establish third-party provenance or protect against an attacker rewriting an entire unanchored export.
