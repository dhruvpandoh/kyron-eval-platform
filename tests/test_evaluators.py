from backend.app.core import (
    evaluate_trace,
    load_scenarios,
    run_suite,
    simulate_scenario,
)


def test_v2_passes_all_current_scenarios():
    output = run_suite("v2")
    assert all(item["evaluation"]["passed"] for item in output["results"])


def test_v1_exposes_expected_failures():
    output = run_suite("v1")
    by_id = {item["scenario_id"]: item for item in output["results"]}

    assert not by_id["schedule_correction"]["evaluation"]["passed"]
    assert not by_id["schedule_tool_failure"]["evaluation"]["claim_grounded"]
    assert not by_id["refill_urgent_symptom"]["evaluation"]["safety"]


def test_dataset_has_two_workflows_and_controls():
    scenarios = load_scenarios()

    assert len({s["workflow"] for s in scenarios}) >= 2
    assert any(s["difficulty"] == "control" for s in scenarios)
    assert any(s["difficulty"] == "safety" for s in scenarios)


def get_scenario(scenario_id: str):
    scenarios = load_scenarios()

    return next(
        scenario
        for scenario in scenarios
        if scenario["id"] == scenario_id
    )


def test_tool_failure_not_counted_as_completion():
    scenario = get_scenario("schedule_tool_failure")

    run = simulate_scenario(scenario, "v1")
    evaluation = evaluate_trace(scenario, run)

    assert evaluation["task_completion"] == 0
    assert evaluation["claim_grounded"] == 0
    assert run["final_state"]["appointment"] is None
    assert "unsupported_success_claim" in evaluation["failure_reasons"]


def test_caller_correction_is_handled_by_v2():
    scenario = get_scenario("schedule_correction")

    v1_run = simulate_scenario(scenario, "v1")
    v2_run = simulate_scenario(scenario, "v2")

    v1_eval = evaluate_trace(scenario, v1_run)
    v2_eval = evaluate_trace(scenario, v2_run)

    assert v1_eval["task_completion"] == 0
    assert v1_eval["critical_entity_accuracy"] < 1

    assert v2_eval["task_completion"] == 1
    assert v2_eval["critical_entity_accuracy"] == 1.0

    assert (
        v2_run["final_state"]["appointment"]["date"]
        == scenario["expected"]["date"]
    )


def test_urgent_symptoms_escalate_before_routine_action():
    scenario = get_scenario("refill_urgent_symptom")

    run = simulate_scenario(scenario, "v2")
    evaluation = evaluate_trace(scenario, run)

    assert run["final_state"]["escalated"] is True
    assert evaluation["safety"] == 1

    tool_events = [
        item
        for item in run["trace"]
        if item["type"] == "tool"
    ]

    tool_names = [item["tool"] for item in tool_events]

    assert "escalate_urgent" in tool_names
    assert "submit_refill" not in tool_names