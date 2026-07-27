# Daily Driver Hypotheses

Status: active during the current observation window.
Owner: release owner / operator running the ritual.

This file tracks changes that are currently shipped but are not yet validated by
real daily-driver usage.

## Rules

- Observed bug fixes stay listed as observed fixes.
- Hypotheses under test do not get rewritten as findings before usage evidence
  exists.
- Promotion requires concrete friction-log evidence, a reproduced task, or a
  repeated real-user demand pattern.
- Rejection is allowed. A shipped hypothesis that does not earn its keep should
  be removed.

## Current State

| Item | Status | Why it exists now | What validates it | What kills it |
| --- | --- | --- | --- | --- |
| Ticker sanitization for finance memory (`DCF`, `WACC`, `EPS` excluded from ticker extraction) | Observed fix | Non-ticker finance abbreviations in a symbols field are objectively wrong on their face | Quick action or usage log shows finance context stays clean without polluting symbols | Reproduced evidence that the sanitization breaks legitimate ticker capture |
| Finance workflow and response-shaping changes around `FINANCE_ANALYST` | Hypothesis under test | Reasonable bet, but not grounded in a real trading-day log yet | Repeated real usage shows the finance mode reduces friction or improves task completion | No real usage demand, or friction shows the mode adds confusion or unnecessary branching |
| Additional workflow fixes inferred from prior speculation rather than observed logs | Hypothesis under test | They may be directionally right, but they were not sourced from a real friction run | Friction entries and repeated tasks independently point at the same problem | The log stays empty, or the real friction points elsewhere |

## Review Cadence

1. Run the daily-driver ritual.
2. Log product friction in [FRICTION.md](../../FRICTION.md).
3. Log environment bailouts separately in the runbook notes.
4. Review this ledger only after there is actual usage data.
5. For each hypothesis, decide: promote, keep under test, or remove.
