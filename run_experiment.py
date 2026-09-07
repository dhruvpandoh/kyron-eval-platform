from __future__ import annotations

import json
from pathlib import Path

from backend.app.core import compare_manual_labels, run_suite

ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / "artifacts"
ARTIFACTS.mkdir(exist_ok=True)

runs = {version: run_suite(version) for version in ("v1", "v2")}
for version, output in runs.items():
    (ARTIFACTS / f"sample_run_{version}.json").write_text(json.dumps(output, indent=2))

comparison = {
    "hypothesis": "v2 should improve safety and truthfulness by honoring caller corrections, grounding success claims in tool results, retrying one transient booking failure, and escalating urgent symptoms before routine automation.",
    "v1": runs["v1"]["summary"],
    "v2": runs["v2"]["summary"],
    "deltas": {
        key: round(runs["v2"]["summary"][key] - runs["v1"]["summary"][key], 3)
        for key in ["pass_rate", "avg_score", "task_completion", "claim_grounding", "safety", "clarity"]
    },
}
(ARTIFACTS / "comparison.json").write_text(json.dumps(comparison, indent=2))

manual = compare_manual_labels(runs)
(ARTIFACTS / "manual_vs_automated_clarity.json").write_text(json.dumps(manual, indent=2))

print(json.dumps(comparison, indent=2))
print("Manual-label agreement:", manual["agreement"])
