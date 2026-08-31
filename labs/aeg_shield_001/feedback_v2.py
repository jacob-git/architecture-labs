from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import math

from .core import Decision, GovernanceDecision, Proposal


@dataclass(frozen=True)
class EvidenceRecordV2:
    change_type: str
    environment: str
    correlation_id: str
    producer: str
    occurred_at: datetime
    severity: float
    reason: str


@dataclass
class EvidenceMemoryV2:
    trusted_producers: set[str] = field(default_factory=lambda: {"shield-runtime"})
    half_life_days: float = 30.0
    max_penalty: float = 0.60
    records: list[EvidenceRecordV2] = field(default_factory=list)

    def ingest(self, evidence: EvidenceRecordV2) -> bool:
        if evidence.producer not in self.trusted_producers:
            return False
        self.records.append(evidence)
        return True

    def penalty_for(self, change_type: str, environment: str, *, now: datetime) -> float:
        latest_by_correlation: dict[str, EvidenceRecordV2] = {}
        for record in self.records:
            if record.change_type != change_type or record.environment != environment:
                continue
            age_days = max(0.0, (now - record.occurred_at).total_seconds() / 86400.0)
            if age_days > self.half_life_days * 6:
                continue
            prior = latest_by_correlation.get(record.correlation_id)
            if prior is None or record.severity > prior.severity:
                latest_by_correlation[record.correlation_id] = record

        total = 0.0
        for record in latest_by_correlation.values():
            age_days = max(0.0, (now - record.occurred_at).total_seconds() / 86400.0)
            decay = math.pow(0.5, age_days / self.half_life_days)
            total += record.severity * decay
        return min(self.max_penalty, total)


class AEGGovernorV2:
    def __init__(self, memory: EvidenceMemoryV2, environment: str, allow_threshold: float = 0.70):
        self.memory = memory
        self.environment = environment
        self.allow_threshold = allow_threshold

    def evaluate(self, proposal: Proposal, *, now: datetime | None = None) -> GovernanceDecision:
        now = now or datetime.now(timezone.utc)
        penalty = self.memory.penalty_for(proposal.change_type, self.environment, now=now)
        effective_risk = min(1.0, proposal.risk_score + penalty)
        if effective_risk >= self.allow_threshold:
            return GovernanceDecision(proposal.proposal_id, Decision.DENY, f"effective risk {effective_risk:.2f} reached threshold {self.allow_threshold:.2f}", penalty)
        return GovernanceDecision(proposal.proposal_id, Decision.ALLOW, f"effective risk {effective_risk:.2f} below threshold {self.allow_threshold:.2f}", penalty)
