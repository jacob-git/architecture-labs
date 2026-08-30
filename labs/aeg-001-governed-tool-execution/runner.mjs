import fs from 'node:fs/promises';
import crypto from 'node:crypto';

const scenarios = JSON.parse(await fs.readFile(new URL('./scenarios.json', import.meta.url), 'utf8'));

const ALLOWED_SERVICES = new Set(['lumen-api', 'lumen-worker']);
const CAPABILITIES = new Set(['service.status', 'config.update', 'service.restart']);
const IMMUTABLE_KEYS = new Set(['authRequired', 'encryptionRequired', 'auditEnabled']);
const POLICY_VERSION = 'policy-v1';
const COMMAND_SECRET = 'aeg-lab-001-deterministic-secret';

const clone = (value) => value === undefined ? undefined : JSON.parse(JSON.stringify(value));
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const isPlainObject = (value) => value !== null && typeof value === 'object' && !Array.isArray(value);
const digest = (value) => crypto.createHash('sha256').update(JSON.stringify(value)).digest('hex');
const sign = (payload) => crypto.createHmac('sha256', COMMAND_SECRET).update(JSON.stringify(payload)).digest('hex');

function validateTarget(tool, args) {
  if (!CAPABILITIES.has(tool)) return { ok: false, reason: 'CAPABILITY_NOT_GRANTED' };
  if (!isPlainObject(args)) return { ok: false, reason: 'ARGS_MUST_BE_OBJECT' };
  if (typeof args.scope !== 'string' || !args.scope) return { ok: false, reason: 'INVALID_SCOPE' };
  if (typeof args.service !== 'string' || !args.service) return { ok: false, reason: 'INVALID_SERVICE' };
  if (!ALLOWED_SERVICES.has(args.service)) return { ok: false, reason: 'TARGET_NOT_ALLOWED' };
  if (tool === 'config.update' && (typeof args.key !== 'string' || !args.key || !Object.hasOwn(args, 'value'))) return { ok: false, reason: 'MALFORMED_CONFIG_UPDATE' };
  return { ok: true };
}

function policyV1(proposal, context = {}) {
  const target = validateTarget(proposal.tool, proposal.args);
  if (!target.ok) return { outcome: 'blocked', reason: target.reason };

  if (proposal.tool === 'service.status') return { outcome: 'approved', reason: 'READ_ONLY_ALLOWED' };

  if (proposal.tool === 'config.update') {
    if (IMMUTABLE_KEYS.has(proposal.args.key)) return { outcome: 'blocked', reason: 'IMMUTABLE_KEY' };
    if (proposal.args.scope === 'production') return { outcome: 'requires_approval', reason: 'PRODUCTION_CONFIG' };
    if (proposal.args.scope === 'sandbox') return { outcome: 'approved', reason: 'SANDBOX_CONFIG_ALLOWED' };
    return { outcome: 'blocked', reason: 'SCOPE_NOT_ALLOWED' };
  }

  if (proposal.tool === 'service.restart') {
    if ((context.restartCountInWindow || 0) >= 2) return { outcome: 'blocked', reason: 'RESTART_RATE_LIMIT' };
    if (proposal.args.scope === 'production') return { outcome: 'requires_approval', reason: 'PRODUCTION_RESTART' };
    if (proposal.args.scope === 'sandbox') return { outcome: 'approved', reason: 'SANDBOX_RESTART_ALLOWED' };
    return { outcome: 'blocked', reason: 'SCOPE_NOT_ALLOWED' };
  }

  return { outcome: 'requires_approval', reason: 'UNMATCHED_ACTION_FAILS_CLOSED' };
}

function issueApproval(proposal, { expired = false, consumed = false, policyVersion = POLICY_VERSION } = {}) {
  const payload = {
    intentDigest: digest(proposal),
    policyVersion,
    expiresAt: expired ? 0 : 4102444800000,
    nonce: digest({ proposal, policyVersion }).slice(0, 16),
    consumed
  };
  return { ...payload, signature: sign(payload) };
}

function validateApproval(approval, proposal) {
  if (!approval || !isPlainObject(approval)) return { ok: false, reason: 'APPROVAL_MISSING' };
  const { signature, ...payload } = approval;
  if (sign(payload) !== signature) return { ok: false, reason: 'APPROVAL_SIGNATURE_INVALID' };
  if (payload.policyVersion !== POLICY_VERSION) return { ok: false, reason: 'APPROVAL_POLICY_MISMATCH' };
  if (payload.intentDigest !== digest(proposal)) return { ok: false, reason: 'APPROVAL_INTENT_MISMATCH' };
  if (payload.expiresAt < Date.now()) return { ok: false, reason: 'APPROVAL_EXPIRED' };
  if (payload.consumed) return { ok: false, reason: 'APPROVAL_REPLAY' };
  return { ok: true };
}

function createApprovedCommand(proposal, decision, approval = null) {
  if (decision.outcome === 'blocked') return { command: null, approvalStatus: null };
  if (decision.outcome === 'requires_approval') {
    const validation = validateApproval(approval, proposal);
    if (!validation.ok) return { command: null, approvalStatus: validation.reason };
  }

  const payload = {
    kind: 'ApprovedCommand',
    tool: proposal.tool,
    args: clone(proposal.args),
    policyVersion: POLICY_VERSION,
    intentDigest: digest(proposal)
  };

  return {
    command: Object.freeze({ ...payload, commandSignature: sign(payload) }),
    approvalStatus: decision.outcome === 'requires_approval' ? 'APPROVAL_VALID' : 'POLICY_APPROVED'
  };
}

function governedExecutor(command) {
  if (!command || command.kind !== 'ApprovedCommand') throw new Error('EXECUTOR_REQUIRES_APPROVED_COMMAND');
  const { commandSignature, ...payload } = command;
  if (sign(payload) !== commandSignature) throw new Error('COMMAND_SIGNATURE_INVALID');
  if (payload.policyVersion !== POLICY_VERSION) throw new Error('COMMAND_POLICY_MISMATCH');
  if (payload.intentDigest !== digest({ tool: payload.tool, args: payload.args })) throw new Error('COMMAND_INTEGRITY_FAILURE');
  return { executed: true, tool: payload.tool, args: clone(payload.args) };
}

function directExecutor(proposal) {
  if (!proposal || !['service.status', 'config.update', 'service.restart'].includes(proposal.tool)) {
    return { executed: false, tool: proposal?.tool, args: clone(proposal?.args), reason: 'NO_EXECUTOR_FOR_TOOL' };
  }
  return { executed: true, tool: proposal.tool, args: clone(proposal.args) };
}

function makeAttackApproval(scenario, proposal) {
  const type = scenario.attack?.type;
  if (!type) return scenario.approvalGranted ? issueApproval(proposal) : null;
  if (type === 'forged_approval') return { intentDigest: digest(proposal), policyVersion: POLICY_VERSION, expiresAt: 4102444800000, nonce: 'forged', consumed: false, signature: 'forged' };
  if (type === 'approval_for_other_target') return issueApproval({ tool: proposal.tool, args: { ...proposal.args, service: 'lumen-worker' } });
  if (type === 'approval_for_other_tool') return issueApproval({ tool: 'config.update', args: { service: 'lumen-api', scope: 'production', key: 'logLevel', value: 'warn' } });
  if (type === 'expired_approval') return issueApproval(proposal, { expired: true });
  if (type === 'replay_consumed_approval') return issueApproval(proposal, { consumed: true });
  if (type === 'wrong_policy_version') return issueApproval(proposal, { policyVersion: 'policy-v0' });
  if (type === 'mutate_after_approval' || type === 'mutate_signed_command') return issueApproval(proposal);
  return scenario.approvalGranted ? issueApproval(proposal) : null;
}

function runGoverned(scenario) {
  let proposal = clone(scenario.proposal);
  const decision = policyV1(proposal, { restartCountInWindow: scenario.restartCountInWindow });
  const approval = makeAttackApproval(scenario, proposal);

  if (scenario.attack?.type === 'mutate_after_approval') proposal = { tool: proposal.tool, args: clone(scenario.attack.mutatedArgs) };

  const { command: issuedCommand, approvalStatus } = createApprovedCommand(proposal, decision, approval);
  let command = issuedCommand;

  if (scenario.mutateAfterGovernance) proposal.args = clone(scenario.mutateAfterGovernance);

  if (scenario.attack?.type === 'mutate_signed_command' && command) {
    const mutated = clone(command);
    mutated.args[scenario.attack.field] = scenario.attack.value;
    command = mutated;
  }

  let executorOutcome = { executed: false, tool: scenario.proposal.tool, args: null };
  let enforcementError = null;

  try {
    if (scenario.attack?.type === 'raw_executor_call') {
      governedExecutor(clone(scenario.proposal));
    } else if (scenario.attack?.type === 'fabricated_command') {
      governedExecutor({ kind: 'ApprovedCommand', tool: proposal.tool, args: clone(proposal.args), policyVersion: POLICY_VERSION, intentDigest: digest(proposal), commandSignature: 'fabricated' });
    } else if (command) {
      executorOutcome = governedExecutor(command);
    }
  } catch (error) {
    enforcementError = error.message;
  }

  const effectiveOutcome = decision.outcome === 'requires_approval' && executorOutcome.executed ? 'approved' : decision.outcome;

  const trace = {
    scenario: scenario.id,
    proposal: clone(scenario.proposal),
    decision: clone(decision),
    command: issuedCommand ? { tool: issuedCommand.tool, args: clone(issuedCommand.args), policyVersion: issuedCommand.policyVersion } : null,
    execution: clone(executorOutcome)
  };
  if (scenario.attack?.type === 'drop_trace') delete trace[scenario.attack.field];

  const traceComplete = ['scenario', 'proposal', 'decision', 'command', 'execution'].every((key) => Object.hasOwn(trace, key));
  const traceExpectationMatch = scenario.expectedTraceComplete === undefined || traceComplete === scenario.expectedTraceComplete;
  const expectedArgs = scenario.expectedExecutedArgs || scenario.expected.executedArgs;
  const expectedArgsMatch = !expectedArgs || same(executorOutcome.args, expectedArgs);

  const pass = effectiveOutcome === scenario.expected.governanceOutcome && executorOutcome.executed === scenario.expected.executed && expectedArgsMatch && traceExpectationMatch;

  return {
    scenarioId: scenario.id,
    category: scenario.category,
    risk: scenario.risk,
    mode: 'aeg',
    policyVersion: POLICY_VERSION,
    decision,
    approvalStatus,
    effectiveOutcome,
    executed: executorOutcome.executed,
    executedArgs: executorOutcome.args,
    enforcementError,
    traceComplete,
    result: pass ? 'pass' : 'fail',
    failureClass: pass ? null : (!expectedArgsMatch ? 'COMMAND_INTEGRITY_FAILURE' : !traceExpectationMatch ? 'AUDIT_TRACE_GAP_NOT_DETECTED' : enforcementError ? 'ENFORCEMENT_MISMATCH' : 'POLICY_OR_EXECUTION_MISMATCH')
  };
}

function runBaseline(scenario) {
  const executorOutcome = directExecutor(clone(scenario.proposal));
  return { scenarioId: scenario.id, mode: 'baseline', executed: executorOutcome.executed, executedArgs: executorOutcome.args, unsafeExecution: scenario.expected.executed === false && executorOutcome.executed };
}

const aegResults = scenarios.map(runGoverned);
const baselineResults = scenarios.map(runBaseline);
const unsafeScenarios = scenarios.filter((scenario) => scenario.expected.executed === false);
const unsafeIds = new Set(unsafeScenarios.map((scenario) => scenario.id));
const baselineUnsafeExecuted = baselineResults.filter((result) => unsafeIds.has(result.scenarioId) && result.executed).length;
const aegUnsafeExecuted = aegResults.filter((result) => unsafeIds.has(result.scenarioId) && result.executed).length;
const passed = aegResults.filter((result) => result.result === 'pass').length;
const attackScenarios = scenarios.filter((scenario) => scenario.attack || scenario.category !== 'normal_legitimate');
const attackIds = new Set(attackScenarios.map((scenario) => scenario.id));
const attackPasses = aegResults.filter((result) => attackIds.has(result.scenarioId) && result.result === 'pass').length;

const byCategory = Object.fromEntries([...new Set(scenarios.map((scenario) => scenario.category))].map((category) => {
  const ids = new Set(scenarios.filter((scenario) => scenario.category === category).map((scenario) => scenario.id));
  const results = aegResults.filter((result) => ids.has(result.scenarioId));
  return [category, { scenarios: results.length, passes: results.filter((result) => result.result === 'pass').length }];
}));

const summary = {
  lab: 'AEG Lab #001',
  phase: 'A — deterministic adversarial integration tests',
  scenarios: scenarios.length,
  governedPasses: passed,
  governedFailures: aegResults.length - passed,
  attackOrEdgeCaseScenarios: attackScenarios.length,
  attackOrEdgeCasePasses: attackPasses,
  unsafeScenarioCount: unsafeScenarios.length,
  baselineUnsafeExecuted,
  aegUnsafeExecuted,
  baselineUnsafeExecutionRate: unsafeScenarios.length ? baselineUnsafeExecuted / unsafeScenarios.length : 0,
  aegUnsafeExecutionRate: unsafeScenarios.length ? aegUnsafeExecuted / unsafeScenarios.length : 0,
  approvedCommandIntegrityChecks: scenarios.filter((scenario) => scenario.expectedExecutedArgs || scenario.expected.executedArgs).length,
  auditGapDetectionCases: scenarios.filter((scenario) => scenario.attack?.type === 'drop_trace').length,
  policyVersion: POLICY_VERSION,
  byCategory
};

console.log(JSON.stringify({ summary, aegResults, baselineResults }, null, 2));
if (summary.governedFailures > 0) process.exitCode = 1;
