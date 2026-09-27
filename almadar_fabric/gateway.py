"""Local trust profile: pinned prompt validation, platform signing and receiver verification.
HMAC is used for this one-process demo; it is not the Catalyst's JWS/PKI profile.
"""

from copy import deepcopy
import hmac
import secrets
from .audit import digest
from .models import DispatchDenied
from .process import FIELDS, render_prompt


class GovernanceObserver:
    def __init__(self):
        self.scores, self.events = {}, []

    def observe(self, agent, verdict, reason):
        delta = {"ALLOW": 0.05, "REDACT": -0.01, "BLOCK": -1.05}[verdict]
        self.scores[agent] = round(self.scores.get(agent, 5.0) + delta, 2)
        self.events.append(
            {
                "agent": agent,
                "verdict": verdict,
                "reason": reason,
                "score": self.scores[agent],
                "advisory_only": True,
            }
        )


class TrustGateway:
    def __init__(self, audit, observer):
        self.audit, self.observer, self.key = audit, observer, secrets.token_bytes(32)
        self.passports = set()

    def sign(self, payload, template, incident, registry):
        payload = deepcopy(payload)
        actor = payload["initiator"]
        try:
            if actor not in template["allowed_initiators"]:
                raise DispatchDenied("Initiator does not own this process handoff")
            card = registry.cards.get(payload["executor"])
            if (
                not card
                or not card["onboarded"]
                or payload["skill"] not in card["skills"]
            ):
                raise DispatchDenied(
                    "Executor is not onboarded for the requested capability"
                )
            prompt = payload["structured_prompt"]
            if (
                set(prompt) != set(FIELDS)
                or payload["template_hash"] != template["template_hash"]
                or payload["activity"] != template["id"]
                or payload["skill"] != template["skill"]
            ):
                raise DispatchDenied("Task does not match its pinned template")
            if prompt["Task Context"]["incident_id"] != incident.incident_id or prompt[
                "Target Object"
            ] != {
                "transport_id": incident.transport_id,
                "cell_ids": list(incident.cell_ids),
            }:
                raise DispatchDenied("Task target is outside the authorised incident")
            if (
                prompt["Constraints"]["bulk_reset_allowed"]
                or prompt["Constraints"]["scope"] != "incident-only"
            ):
                raise DispatchDenied("Unsafe action requires operator review")
            if not set(template["required_evidence"]) <= set(payload["evidence"]):
                raise DispatchDenied("Required predecessor evidence is missing")
            if prompt != render_prompt(template, incident, payload["evidence"]):
                raise DispatchDenied(
                    "Structured prompt differs from the operator template"
                )
            if "subscriber_ids" in payload:
                payload.pop("subscriber_ids")
                self.observer.observe(
                    actor,
                    "REDACT",
                    "Subscriber identifiers removed; only aggregate impact may cross the boundary",
                )
                self.audit.append("redact", actor, "TDG removed subscriber identifiers")
            passport = {
                "id": secrets.token_hex(8),
                "intent_hash": digest(payload),
                "incident_id": incident.incident_id,
                "executor": payload["executor"],
                "profile": "local-hmac-v1",
            }
            signature = hmac.new(
                self.key, digest(passport).encode(), "sha256"
            ).hexdigest()
            self.audit.append(
                "sign",
                actor,
                "Platform attested incident-scoped dispatch",
                passport=passport,
            )
            return {"payload": payload, "passport": passport, "signature": signature}
        except DispatchDenied as exc:
            self.observer.observe(actor, "BLOCK", str(exc))
            self.audit.append("block", actor, str(exc))
            raise

    def verify(self, envelope, receiver):
        passport = envelope["passport"]
        expected = hmac.new(self.key, digest(passport).encode(), "sha256").hexdigest()
        if (
            not hmac.compare_digest(expected, envelope["signature"])
            or digest(envelope["payload"]) != passport["intent_hash"]
            or passport["executor"] != receiver
            or passport["id"] in self.passports
        ):
            self.observer.observe(
                receiver,
                "BLOCK",
                "Signature, intent, receiver or replay validation failed",
            )
            self.audit.append(
                "block", receiver, "Receiver rejected altered or replayed dispatch"
            )
            raise DispatchDenied("Receiver rejected altered or replayed dispatch")
        self.passports.add(passport["id"])
        self.observer.observe(
            receiver, "ALLOW", "Pinned request and platform attestation verified"
        )
        self.audit.append(
            "verify",
            receiver,
            "Receiver verified platform attestation",
            passport_id=passport["id"],
            intent_hash=passport["intent_hash"],
        )
        return envelope["payload"]
