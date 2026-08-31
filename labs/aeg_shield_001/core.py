from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable


class Decision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


class RuntimeAction(str, Enum):
    NONE = "none"
    CONTAIN = "contain"
    ROLLBACK = "rollback"


@dataclass(frozen=True)
class Proposal:
    proposal_id: str
    change_type: str
    risk_score: float
    predicted_error_rate: float
    predicted_latency_ms: float


@dataclass(frozen=True)
class GovernanceDecision:
    proposal_id: str
    decision: Decision
    reason: str
    learned_penalty: float


@dataclass(frozen=True)
class RuntimeObservation:
    error_rate: float
    latency_ms: float
    policy_violation: bool = False


@dataclass(frozen=True)
class ShieldOutcome:
    action: RuntimeAction
    reason: str
    severe: bool


@dataclass(frozen=True)
class IncidentEvidence:
    change_type: str
    severity: float
    reason: str


@dataclass
class EvidenceMemory:
    penalties: dict[str, float] = field(default_factory=dict)

    def penalty_for(self, change_type: str) -> float:
        return self.penalties.get(change_type, 0.0)

    def ingest(self, evidence: IncidentEvidence) -> None:
        current = self.penalties.get(evidence.change_type, 0.0)
        self.penalties[evidence.change_type] = min(1.0, current + evidence.severity)


class AEGGovernor:
    """A deliberately small governance boundary for the integration experiment."""

    def __init__(self, memory: EvidenceMemory, allow_threshold: float = 0.70):
        self.memory = memory
        self.allow_threshold = allow_threshold

    def evaluate(self, proposal: Proposal) -> GovernanceDecision:
        penalty = self.memory.penalty_for(proposal.change_type)
        effective_risk = min(1.0, proposal.risk_score + penalty)
        if effective_risk >= self.allow_threshold:
            return GovernanceDecision(
                proposal_id=proposal.proposal_id,
                decision=Decision.DENY,
                reason=f"effective risk {effective_risk:.2f} reached threshold {self.allow_threshold:.2f}",
                learned_penalty=penalty,
            )
        return GovernanceDecision(
            proposal_id=proposal.proposal_id,
            decision=Decision.ALLOW,
            reason=f"effective risk {effective_risk:.2f} below threshold {self.allow_threshold:.2f}",
            learned_penalty=penalty,
        )


class SHIELDMonitor:
    def __init__(self, max_error_rate: float = 0.05, max_latency_ms: float = 500.0):
        self.max_error_rate = max_error_rate
        self.max_latency_ms = max_latency_ms

    def inspect(self, observation: RuntimeObservation) -> ShieldOutcome:
        if observation.policy_violation:
            return ShieldOutcome(RuntimeAction.ROLLBACK, "runtime policy violation", True)
        if observation.error_rate > self.max_error_rate and observation.latency_ms > self.max_latency_ms:
            return ShieldOutcome(RuntimeAction.ROLLBACK, "error rate and latency breached", True)
        if observation.error_rate > self.max_error_rate:
            return ShieldOutcome(RuntimeAction.CONTAIN, "error rate breached", False)
        if observation.latency_ms > self.max_latency_ms:
            return ShieldOutcome(RuntimeAction.CONTAIN, "latency breached", False)
        return ShieldOutcome(RuntimeAction.NONE, "runtime remained inside guardrails", False)


def evidence_from(change_type: str, outcome: ShieldOutcome) -> IncidentEvidence | None:
    if outcome.action is RuntimeAction.NONE:
        return None
    severity = 0.45 if outcome.severe else 0.25
    return IncidentEvidence(change_type=change_type, severity=severity, reason=outcome.reason)


def run_learning_cycle(
    proposal: Proposal,
    observation: RuntimeObservation,
    *,
    memory: EvidenceMemory | None = None,
) -> dict[str, object]:
    memory = memory or EvidenceMemory()
    governor = AEGGovernor(memory)
    shield = SHIELDMonitor()

    before = governor.evaluate(proposal)
    outcome = RuntimeAction.NONE
    evidence = None

    if before.decision is Decision.ALLOW:
        shield_outcome = shield.inspect(observation)
        outcome = shield_outcome.action
        evidence = evidence_from(proposal.change_type, shield_outcome)
        if evidence:
            memory.ingest(evidence)

    after = governor.evaluate(proposal)
    return {
        "before": before,
        "runtime_action": outcome,
        "evidence": evidence,
        "after": after,
        "memory": dict(memory.penalties),
    }


def run_scenarios() -> list[dict[str, object]]:
    scenarios: Iterable[tuple[str, Proposal, RuntimeObservation]] = [
        (
            "safe_change",
            Proposal("safe-1", "cache_ttl", 0.20, 0.01, 150),
            RuntimeObservation(error_rate=0.01, latency_ms=180),
        ),
        (
            "latent_failure",
            Proposal("latent-1", "routing_rule", 0.35, 0.02, 220),
            RuntimeObservation(error_rate=0.18, latency_ms=860),
        ),
        (
            "policy_violation",
            Proposal("policy-1", "tool_permission", 0.30, 0.01, 180),
            RuntimeObservation(error_rate=0.01, latency_ms=190, policy_violation=True),
        ),
    ]

    results = []
    for name, proposal, observation in scenarios:
        cycle = run_learning_cycle(proposal, observation)
        cycle["scenario"] = name
        results.append(cycle)
    return results
