# Product findings

## Release recommendation

I would not ship the v1 behavior represented in this experiment. The test suite exposed two issues I would treat as release blockers, plus one high-priority correctness problem.

### P0 — Completion claims not grounded in tool state

In `schedule_tool_failure`, v1 gets an `upstream_timeout` from the booking tool but still tells the caller that the appointment is booked.

This is the most concerning failure in the suite because the conversation sounds successful, while the actual system state shows that nothing was booked.

**Intervention:** only allow the agent to use completion language after the underlying tool confirms success. I would also distinguish retryable and non-retryable tool failures and add more regression cases around timeouts, retries, partial failures, and duplicate requests.

**Verification:** run an injected-failure test suite and require zero unsupported completion claims. In production, I would also sample cases where agent claims and tool state disagree.

### P0 — Missed urgent escalation

In `refill_urgent_symptom`, v1 continues with the refill workflow even though the scenario policy says the caller should be routed urgently.

I would treat this as a release blocker because safety routing should take priority over completing a routine workflow.

**Intervention:** evaluate urgent or safety conditions before performing routine side effects, and preserve the relevant caller context when handing the interaction off to a human.

**Verification:** add synthetic tests around urgent-policy boundaries and manually review urgent traces during an initial production rollout.

### P1 — Stale critical entities after caller corrections

The `appointment_correction` and `refill_pharmacy_change` scenarios show a state-management issue where the agent keeps using an earlier value even after the caller corrects it.

**Intervention:** treat critical entities such as appointment date, provider, and pharmacy as explicit conversation state. The latest clear correction should replace the old value, and I would require confirmation before taking a side effect when one of those fields changes.

**Verification:** add scenario families covering corrections, interruptions, and reconfirmation, and compare the final tool arguments against the caller's final stated intent.

## What I would not conclude

I would not treat the failure rates in this experiment as estimates of how often these problems happen in production.

The six scenarios were intentionally chosen to stress specific failure modes. Before prioritizing issues based on frequency, I would want real workflow volume, tool error rates, sampled human labels, customer-specific policies, and production traces involving corrections, failures, and escalations.