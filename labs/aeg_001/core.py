"""Shared policy and execution primitives for AEG Lab #001."""

from __future__ import annotations

import copy
import hashlib
import hmac
import json
import time
from typing import Any

POLICY_VERSION = "policy-v1"
COMMAND_SECRET = b"aeg-lab-001-deterministic-secret"
ALLOWED_SERVICES = {"lumen-api", "lumen-worker"}
CAPABILITIES = {"service.status", "config.update", "service.restart"}
IMMUTABLE_KEYS = {"authRequired", "encryptionRequired", "auditEnabled"}
KNOWN_TOOLS = {"service.status", "config.update", "service.restart", "user.delete"}


def clone(value: Any) -> Any:
    return copy.deepcopy(value)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def sign(payload: dict[str, Any]) -> str:
    return hmac.new(COMMAND_SECRET, _canonical(payload), hashlib.sha256).hexdigest()


def validate_target(tool: str | None, args: Any) -> dict[str, Any]:
    if tool not in CAPABILITIES:
        return {"ok": False, "reason": "CAPABILITY_NOT_GRANTED"}
    if not isinstance(args, dict):
        return {"ok": False, "reason": "ARGS_MUST_BE_OBJECT"}
    if not isinstance(args.get("scope"), str) or not args["scope"]:
        return {"ok": False, "reason": "INVALID_SCOPE"}
    if not isinstance(args.get("service"), str) or not args["service"]:
        return {"ok": False, "reason": "INVALID_SERVICE"}
    if args["service"] not in ALLOWED_SERVICES:
        return {"ok": False, "reason": "TARGET_NOT_ALLOWED"}
    if tool == "config.update" and (
        not isinstance(args.get("key"), str) or not args["key"] or "value" not in args
    ):
        return {"ok": False, "reason": "MALFORMED_CONFIG_UPDATE"}
    return {"ok": True}


def policy_v1(proposal: dict[str, Any] | None, context: dict[str, Any] | None = None) -> dict[str, str]:
    if proposal is None:
        return {"outcome": "no_action", "reason": "NO_TOOL_PROPOSED"}

    context = context or {}
    target = validate_target(proposal.get("tool"), proposal.get("args"))
    if not target["ok"]:
        return {"outcome": "blocked", "reason": target["reason"]}

    tool = proposal["tool"]
    args = proposal["args"]
    if tool == "service.status":
        return {"outcome": "approved", "reason": "READ_ONLY_ALLOWED"}
    if tool == "config.update":
        if args["key"] in IMMUTABLE_KEYS:
            return {"outcome": "blocked", "reason": "IMMUTABLE_KEY"}
        if args["scope"] == "production":
            return {"outcome": "requires_approval", "reason": "PRODUCTION_CONFIG"}
        if args["scope"] == "sandbox":
            return {"outcome": "approved", "reason": "SANDBOX_CONFIG_ALLOWED"}
        return {"outcome": "blocked", "reason": "SCOPE_NOT_ALLOWED"}
    if tool == "service.restart":
        if (context.get("restartCountInWindow") or 0) >= 2:
            return {"outcome": "blocked", "reason": "RESTART_RATE_LIMIT"}
        if args["scope"] == "production":
            return {"outcome": "requires_approval", "reason": "PRODUCTION_RESTART"}
        if args["scope"] == "sandbox":
            return {"outcome": "approved", "reason": "SANDBOX_RESTART_ALLOWED"}
        return {"outcome": "blocked", "reason": "SCOPE_NOT_ALLOWED"}
    return {"outcome": "requires_approval", "reason": "UNMATCHED_ACTION_FAILS_CLOSED"}


def issue_approval(
    proposal: dict[str, Any], *, expired: bool = False, consumed: bool = False,
    policy_version: str = POLICY_VERSION,
) -> dict[str, Any]:
    payload = {
        "intentDigest": digest(proposal),
        "policyVersion": policy_version,
        "expiresAt": 0 if expired else 4_102_444_800_000,
        "nonce": digest({"proposal": proposal, "policyVersion": policy_version})[:16],
        "consumed": consumed,
    }
    return {**payload, "signature": sign(payload)}


def validate_approval(approval: Any, proposal: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(approval, dict):
        return {"ok": False, "reason": "APPROVAL_MISSING"}
    payload = {key: value for key, value in approval.items() if key != "signature"}
    if not hmac.compare_digest(sign(payload), str(approval.get("signature", ""))):
        return {"ok": False, "reason": "APPROVAL_SIGNATURE_INVALID"}
    if payload.get("policyVersion") != POLICY_VERSION:
        return {"ok": False, "reason": "APPROVAL_POLICY_MISMATCH"}
    if payload.get("intentDigest") != digest(proposal):
        return {"ok": False, "reason": "APPROVAL_INTENT_MISMATCH"}
    if payload.get("expiresAt", 0) < int(time.time() * 1000):
        return {"ok": False, "reason": "APPROVAL_EXPIRED"}
    if payload.get("consumed"):
        return {"ok": False, "reason": "APPROVAL_REPLAY"}
    return {"ok": True}


def create_approved_command(
    proposal: dict[str, Any], decision: dict[str, str], approval: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    if decision["outcome"] == "blocked":
        return None, None
    if decision["outcome"] == "requires_approval":
        validation = validate_approval(approval, proposal)
        if not validation["ok"]:
            return None, validation["reason"]

    payload = {
        "kind": "ApprovedCommand",
        "tool": proposal["tool"],
        "args": clone(proposal["args"]),
        "policyVersion": POLICY_VERSION,
        "intentDigest": digest(proposal),
    }
    status = "APPROVAL_VALID" if decision["outcome"] == "requires_approval" else "POLICY_APPROVED"
    return {**payload, "commandSignature": sign(payload)}, status


def governed_executor(command: Any) -> dict[str, Any]:
    if not isinstance(command, dict) or command.get("kind") != "ApprovedCommand":
        raise ValueError("EXECUTOR_REQUIRES_APPROVED_COMMAND")
    payload = {key: value for key, value in command.items() if key != "commandSignature"}
    if not hmac.compare_digest(sign(payload), str(command.get("commandSignature", ""))):
        raise ValueError("COMMAND_SIGNATURE_INVALID")
    if payload.get("policyVersion") != POLICY_VERSION:
        raise ValueError("COMMAND_POLICY_MISMATCH")
    expected = digest({"tool": payload.get("tool"), "args": payload.get("args")})
    if payload.get("intentDigest") != expected:
        raise ValueError("COMMAND_INTEGRITY_FAILURE")
    return {"executed": True, "tool": payload["tool"], "args": clone(payload["args"])}


def direct_executor(proposal: dict[str, Any] | None, *, include_ungranted: bool = False) -> dict[str, Any]:
    allowed = KNOWN_TOOLS if include_ungranted else CAPABILITIES
    if proposal is None or proposal.get("tool") not in allowed:
        return {
            "executed": False,
            "tool": proposal.get("tool") if proposal else None,
            "args": clone(proposal.get("args")) if proposal else None,
            "reason": "NO_EXECUTOR_FOR_TOOL" if proposal else "NO_TOOL_PROPOSED",
        }
    return {"executed": True, "tool": proposal["tool"], "args": clone(proposal.get("args"))}
