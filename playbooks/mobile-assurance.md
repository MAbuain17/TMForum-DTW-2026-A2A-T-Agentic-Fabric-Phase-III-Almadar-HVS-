# Almadar mobile assurance playbook

**Scenario:** degraded mobile broadband across cells sharing a transport path. **Domain:** Assurance. **HVS:** HVS1.

1. Receive a mobile-service anomaly under the operator’s incident scope.
2. Run topology/root-cause analysis and aggregate subscriber-impact analysis in parallel.
3. Wait for both branches before prioritisation. Missing evidence requires operator review.
4. Recommend an incident-scoped transport recovery; block bulk radio resets.
5. Confirm domain-agent availability and backup-path feasibility. Dispatch RAN and core checks, then the simulated transport action.
6. Measure service throughput and packet loss. Close only when both operator thresholds are met; otherwise retain the incident and escalate.

All handoffs use the six-section structured prompt and an incident-bound local platform attestation. No subscriber identifiers are needed for impact reporting. The dashboard exposes evidence, policy observations and audit records for operator inspection.

This is an adapted process using simulated infrastructure. It is not an operational SOP approved by Almadar.
