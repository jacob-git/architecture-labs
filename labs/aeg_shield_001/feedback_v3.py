from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import math

from .core import Decision, GovernanceDecision, Proposal


@dataclass(frozen=True)
class EvidenceRecordV3:
    event_id: str
    source_event_id: str
    change_type: str
    environment: str
    producer: str
    occurred_at: datetime
    severity: float
    kind: str
    reason: str
    signature: str = ""


def _canonical(record: EvidenceRecordV3) -> bytes:
    payload = {
        "source_event_id": record.source_event_id,
        "change_type": record.change_type,
        "environment": record.environment,
        "producer": record.producer,
        "occurred_at": record.occurred_at.astimezone(timezone.utc).isoformat(),
        "severity": round(float(record.severity), 6),
        "kind": record.kind,
        "reason": record.reason,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign_record(record: EvidenceRecordV3, secret: bytes) -> EvidenceRecordV3:
    signature = hmac.new(secret, _canonical(record), hashlib.sha256).hexdigest()
    return replace(record, signature=signature)


@dataclass
class EvidenceMemoryV3:
    producer_secrets: dict[str, bytes] = field(default_factory=lambda: {"shield-runtime": b"phase-e-lab-key"})
    half_life_days: float = 30.0
    max_penalty: float = 0.60
    max_clock_skew: timedelta = timedelta(minutes=5)
    records: list[EvidenceRecordV3] = field(default_factory=list)
    seen_event_ids: set[str] = field(default_factory=set)
    seen_signed_payloads: set[str] = field(default_factory=set)

    def _valid_signature(self, evidence: EvidenceRecordV3) -> bool:
        secret = self.producer_secrets.get(evidence.producer)
        if secret is None:
            return False
        expected = hmac.new(secret, _canonical(evidence), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, evidence.signature)

    def ingest(self, evidence: EvidenceRecordV3, *, now: datetime) -> bool:
        if evidence.kind not in {"incident", "recovery"}:
            return False
        if not 0.0 <= evidence.severity <= 1.0:
            return False
        if evidence.occurred_at > now + self.max_clock_skew:
            return False
        if not self._valid_signature(evidence):
            return False
        if evidence.event_id in self.seen_event_ids:
            return False

        payload_digest = hashlib.sha256(_canonical(evidence)).hexdigest()
        if payload_digest in self.seen_signed_payloads:
            return False

        self.records.append(evidence)
        self.seen_event_ids.add(evidence.event_id)
        self.seen_signed_payloads.add(payload_digest)
        return True

    def penalty_for(self, change_type: str, environment: str, *, now: datetime) -> float:
        by_source: dict[str, list[EvidenceRecordV3]] = {}
        for record in self.records:
            if record.change_type != change_type or record.environment != environment:
                continue
            age_days = (now - record.occurred_at).total_seconds() / 86400.0
            if age_days < 0 or age_days > self.half_life_days * 6:
                continue
            by_source.setdefault(record.source_event_id, []).append(record)

        total = 0.0
        for records in by_source.values():
            ordered = sorted(records, key=lambda item: item.occurred_at)
            latest_recovery = max(
                (r.occurred_at for r in ordered if r.kind == "recovery"),
                default=None,
            )
            incidents = [r for r in ordered if r.kind == "incident"]
            if not incidents:
                continue
            incident = max(incidents, key=lambda item: (item.severity, item.occurred_at))
            if latest_recovery is not None and latest_recovery >= incident.occurred_at:
                continue

            age_days = max(0.0, (now - incident.occurred_at).total_seconds() / 86400.0)
            decay = math.pow(0.5, age_days / self.half_life_days)
            total += incident.severity * decay

        return min(self.max_penalty, total)


class AEGGovernorV3:
    def __init__(self, memory: EvidenceMemoryV3, environment: str, allow_threshold: float = 0.70):
        self.memory = memory
        self.environment = environment
        self.allow_threshold = allow_threshold

    def evaluate(self, proposal: Proposal, *, now: datetime | None = None) -> GovernanceDecision:
        now = now or datetime.now(timezone.utc)
        penalty = self.memory.penalty_for(proposal.change_type, self.environment, now=now)
        effective_risk = min(1.0, proposal.risk_score + penalty)
        if effective_risk >= self.allow_threshold:
            return GovernanceDecision(
                proposal.proposal_id,
                Decision.DENY,
                f"effective risk {effective_risk:.2f} reached threshold {self.allow_threshold:.2f}",
                penalty,
            )
        return GovernanceDecision(
            proposal.proposal_id,
            Decision.ALLOW,
            f"effective risk {effective_risk:.2f} below threshold {self.allow_threshold:.2f}",
            penalty,
        )
