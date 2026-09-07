from __future__ import annotations

import json
from pathlib import Path

from backend.app.core import load_manual_labels, run_suite

ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / "artifacts"

runs = {v: run_suite(v) for v in ("v1", "v2")}
manual = {(x["agent_version"], x["scenario_id"]): x for x in load_manual_labels()}

rows = []
for version, output in runs.items():
    for item in output["results"]:
        key = (version, item["scenario_id"])
        agent_text = " ".join(
            t.get("text", "") for t in item["trace"] if t.get("type") == "agent"
        ).lower()

        # Initial evaluator: sounded plausible, but it confused fluent outcome language with useful clarity.
        v0 = int(any(token in agent_text for token in ["booked", "confirmed", "submitted", "next step", "routing", "route", "couldn’t", "can't"]))
        # Revised evaluator after inspecting disagreements: clarity is only useful if the outcome is also truthful.
        ev = item["evaluation"]
        v1 = int(v0 and ev["task_completion"] and ev["claim_grounded"] and ev["critical_entity_accuracy"] == 1.0)
        label = manual[key]["clarity_label"]
        rows.append({
            "agent_version": version,
            "scenario_id": item["scenario_id"],
            "manual_label": label,
            "manual_note": manual[key]["note"],
            "initial_evaluator_v0": v0,
            "revised_evaluator_v1": v1,
            "v0_agree": v0 == label,
            "v1_agree": v1 == label,
        })

report = {
    "decision_boundary": "Clarity means the patient leaves with a correct, grounded understanding of the outcome and next step; fluent wording alone is insufficient.",
    "initial_problem": "The first evaluator rewarded explicit outcome language even when the agent confidently described the wrong or unconfirmed outcome.",
    "revision": "Gate clarity on system-state task completion, grounded claims, and critical-entity correctness.",
    "v0_agreement": round(sum(r["v0_agree"] for r in rows) / len(rows), 3),
    "v1_agreement": round(sum(r["v1_agree"] for r in rows) / len(rows), 3),
    "rows": rows,
    "caveat": "The revised score is intentionally not presented as a validated production accuracy estimate; the sample is tiny and partly designed around known failure modes. The value is the exposed disagreement and revised decision boundary.",
}
(ARTIFACTS / "clarity_calibration.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
