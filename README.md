# Kyron Eval

A small evaluation platform for healthcare voice-agent workflows.

The main thing I wanted to test was whether the agent actually completed the caller's request safely and correctly, not just whether the conversation sounded good.

The end-to-end flow is:

`scenario → simulated agent interaction → trace → automated evaluation → inspectable result`

## What I focused on

There was more in the assignment than I could reasonably finish in eight hours, so I focused on one complete evaluation loop that I could inspect end to end.

The key design choice was to treat tool and system state as the source of truth for task completion.

For example, an agent can say "your appointment is booked" even if the booking tool failed. The transcript sounds successful, but the real system state says otherwise. That failure mode became the center of the project.

## Architecture

```text
Synthetic scenarios
        ↓
Simulation / replay harness
        ↓
Conversation + tool traces
        ↓
Simulated system state
        ↓
Automated evaluators
        ↓
SQLite
        ↓
FastAPI
        ↓
React dashboard
```

### Backend

- Python
- FastAPI
- SQLite
- deterministic simulator
- rule/state-based evaluators

### Frontend

- React
- TypeScript
- Vite

The UI lets a reviewer:

- see previous evaluation runs
- compare v1 and v2
- inspect failed scenarios
- inspect conversation and tool traces
- see why an evaluator failed a scenario
- add human review notes
- agree with or override an automated result

## Workflows

I used two workflows.

### Appointment scheduling

- normal booking
- caller changes the requested date
- booking tool fails temporarily

### Prescription refill

- normal refill
- caller changes pharmacy
- urgent symptoms appear during the request

I wanted the dataset to include normal cases, state-management problems, tool failures, and a safety case instead of only obvious one-turn failures.

## Ground truth

I do not treat the transcript alone as ground truth.

For appointment booking, the final scheduling-system state tells me whether an appointment was actually created.

For refills, the final refill state tells me whether the request was submitted to the right pharmacy.

For urgent escalation, the escalation state and tool trace tell me whether the required routing actually happened.

This matters because the agent can sound confident while still being wrong.

## Simulation harness

I used a deterministic text-based simulator instead of real phone calls.

Each scenario includes:

- caller goal
- known facts
- tool state
- workflow policy
- expected outcome
- critical entities
- escalation requirements

The harness records:

- caller turns
- agent turns
- tool calls
- tool results
- final state

I chose a deterministic simulator because it made failures reproducible and gave me known ground truth.

What this does not test:

- speech recognition
- interruptions
- latency
- background noise
- TTS quality
- real telephony behavior

## Agent versions

### v1

The baseline intentionally contains a few realistic failure modes:

- keeps stale values after a caller correction
- claims success after a failed tool call
- continues a routine refill flow when urgent escalation is required

### v2

The improved version:

- uses the latest caller correction
- retries one transient booking failure
- only claims success after tool confirmation
- escalates urgent symptoms before routine automation

## Metrics

### Task completion

Did the requested action actually happen?

Evidence comes from final system state.

### Critical entity accuracy

Were important values correct when the action was taken?

Examples include appointment date, time, provider, medication, and pharmacy.

### Claim grounding

Did the agent only claim success when the underlying tool actually succeeded?

### Safety

Did the agent follow the scenario's escalation policy?

### Clarity

Did the caller leave with a correct understanding of what happened and what happens next?

## Evaluator calibration

I manually labeled a small set of traces and compared those labels with the automated clarity evaluator.

The first version was too generous. It rewarded clear wording even when the agent was confidently wrong.

Initial agreement:

`0.667`

I changed the evaluator so that clarity also depends on:

- task completion
- grounded success claims
- correct critical entities

After that change, agreement on this small calibration set became:

`1.0`

I would not treat that as a production accuracy number. The sample is tiny and partly designed around known failure cases.

The useful part was that the disagreement exposed a bad decision boundary and caused me to change the evaluator.

Run:

```bash
PYTHONPATH=. python calibrate_clarity.py
```

## Experiment

I compared v1 and v2 across six synthetic scenarios.

Run:

```bash
PYTHONPATH=. python run_experiment.py
```

Results:

| Metric | v1 | v2 |
|---|---:|---:|
| Pass rate | 33.3% | 100% |
| Average score | 46.2 | 100 |
| Task completion | 33.3% | 100% |
| Claim grounding | 50% | 100% |
| Safety | 83.3% | 100% |
| Clarity | 33.3% | 100% |

I would not interpret v2's 100% as production reliability. It only means v2 passed all six scenarios in this small controlled test set.

## Most important failure

The strongest example is `schedule_tool_failure`.

In v1, the booking tool returns:

```json
{
  "ok": false,
  "error": "upstream_timeout"
}
```

But the agent still tells the caller that the appointment is booked.

The final system state shows:

```json
{
  "appointment": null
}
```

So the conversation sounds successful, but the actual task failed.

That is why I chose to ground completion in system state instead of transcript quality.

In v2, the agent:

1. sees that the tool failed
2. tells the caller the booking is not confirmed yet
3. retries once
4. gets a successful tool result
5. only then confirms the appointment

## Human review

I added a lightweight human-review flow.

A reviewer can:

- add a note
- agree with the evaluator
- override the result to pass
- override the result to fail

The review is saved per scenario result in SQLite.

The original automated evaluation remains visible so the human review does not overwrite the original evidence.

## Product findings

See `docs/PRODUCT_FINDINGS.md`.

The main findings were:

1. unsupported completion claims should block a release
2. missed urgent escalation should block a release
3. stale critical entities after caller corrections are a high-priority correctness issue

I also added targeted regression tests for these three failure classes.

## Production design

If this were processing thousands of calls per day, I would separate trace ingestion, evaluation, and human review.

Production traces would be emitted as structured events containing:

- conversation turns
- tool calls
- tool results
- state changes
- errors
- agent version
- prompt version
- workflow version
- evaluator version

I would store raw traces separately from searchable metadata and evaluation results.

Evaluation would run asynchronously instead of in the live call path.

Cheap deterministic checks could run on every call. More expensive model-based evaluators could run selectively based on risk or sampling.

I would version:

- agent
- model
- prompt
- workflow
- policy
- evaluator
- customer configuration
- tool schema

That would make it possible to compare releases and understand what actually changed when something regressed.

For human review, I would prioritize:

- safety failures
- evaluator disagreements
- agent/tool state mismatches
- a random sample of normal calls

For privacy, I would minimize stored PHI, control access, encrypt stored data and traffic, avoid sensitive values in logs, and set retention policies.

## Intentionally out of scope

I intentionally did not build:

- real phone calls
- STT/TTS
- real EHR integration
- real pharmacy integration
- authentication
- cloud deployment
- large-scale analytics
- a broad workflow library
- a production LLM patient simulator

The main tradeoff was fidelity vs inspectability.

I chose a deterministic simulator because it let me build one reliable, repeatable end-to-end path within the time limit.

## Tests

Run:

```bash
PYTHONPATH=. pytest -q
```

Current suite: 6 tests.

They cover:

- v2 passing the current scenarios
- expected v1 failures
- multiple workflows and safety/control cases
- failed tool calls not counting as completion
- caller corrections being handled correctly
- urgent escalation before routine automation

## Setup

### Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
PYTHONPATH=. uvicorn backend.app.main:app --reload --port 8000
```

FastAPI docs:

`http://localhost:8000/docs`

### Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open:

`http://localhost:5173`

### Run the experiment

```bash
PYTHONPATH=. python run_experiment.py
```

### Run evaluator calibration

```bash
PYTHONPATH=. python calibrate_clarity.py
```

### Run tests

```bash
PYTHONPATH=. pytest -q
```

## Saved artifacts

The repo includes saved example outputs so the project can be reviewed without any external API keys.

```text
artifacts/
├── comparison.json
├── clarity_calibration.json
├── manual_vs_automated_clarity.json
├── sample_run_v1.json
└── sample_run_v2.json
```

## Data and external services

All scenario data is synthetic.

No real patient data, provider data, customer data, recordings, credentials, or API keys are included.

The core project does not require a paid external API.

## AI usage

I used AI tools for brainstorming, code generation, debugging, and documentation.

I did not assume generated code or evaluation logic was correct. I ran the system, inspected traces, tested the evaluators, and changed parts of the implementation when the output did not match the behavior I wanted.

One important decision I made was to use tool and system state as the source of truth for task completion instead of relying on conversation text.

I also changed the clarity evaluator after seeing that it rewarded confident but incorrect answers.

AI helped me move faster, but I based the final decisions on the behavior I observed in the system.

## What I would do next

With more time, I would:

1. add more scenarios around retries, interruptions, ambiguity, and handoffs
2. add customer-specific policy configs
3. add repeated runs with controlled non-determinism
4. add an LLM evaluator alongside deterministic checks
5. compare human labels with deterministic and LLM evaluators
6. add evaluator versioning
7. add aggregate failure-pattern views
8. add risk-based human-review queues
9. add release regression gates
10. validate the system on a larger approved or de-identified trace set

## Submission summary

### Where I spent my time

I focused on:

- scenario design
- ground truth
- replay/simulation
- evaluation metrics
- v1 vs v2 comparison
- evaluator calibration
- full-stack investigation UI
- human review
- regression tests

### What I intentionally did not complete

I did not build a real voice stack, real EHR integrations, authentication, cloud deployment, or a large workflow catalog.

I chose to spend the time on one complete evaluation loop that I could inspect and defend.

### How I used AI

I used AI to speed up implementation and debugging, but I validated the outputs by running the system, inspecting traces, comparing evaluator results with manual labels, and changing the implementation when the evidence showed problems.

### What I would do next

The next step would be expanding the scenario set and validating the evaluators on a larger, independently labeled set of traces before using them for production release decisions.
