from app.agents.project_planning.subagents.decomposition.invest import (
    has_bounded_calculation_contract,
)


def test_calculation_scenarios_are_one_bounded_story():
    criteria = [
        "Given valid inputs, when availability is calculated, then use total_minutes, maintenance_minutes, and unavailable_minutes in the formula.",
        "Availability (%) = ((total_minutes - maintenance_minutes - unavailable_minutes) / (total_minutes - maintenance_minutes)) x 100.",
        "Given total_minutes = 43200, maintenance_minutes = 200, and unavailable_minutes = 100, when calculated, then return 99.77%.",
        "Given a negative input, when calculation is requested, then reject it with a validation error.",
    ]

    assert has_bounded_calculation_contract(criteria) is True


def test_unrelated_outcomes_do_not_match_calculation_guardrail():
    criteria = [
        "Given a visitor, when they register, then create their account.",
        "Given a registered user, when they sign in, then display their dashboard.",
    ]

    assert has_bounded_calculation_contract(criteria) is False
