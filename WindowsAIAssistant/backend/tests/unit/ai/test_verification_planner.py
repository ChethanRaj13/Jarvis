import pytest

from backend.ai.verification_planner import VerificationPlanner


def test_verification_planner_builds_plan():
    planner = VerificationPlanner()
    
    plan = {
        "sub_goal_plans": [
            {
                "sub_goal_id": "sg1",
                "sub_goal_description": "Setup Python",
                "steps": [
                    {"step_number": 1, "action": "Download Python installer", "tool_or_method": "download"},
                    {"step_number": 2, "action": "Run installer"}
                ]
            }
        ]
    }
    
    verification_plan = planner.build_plan(plan, "Setup Python")
    
    assert verification_plan.plan_id == "verification-setup-python"
    assert len(verification_plan.steps) == 2
    assert verification_plan.steps[0].step_number == 1
    assert verification_plan.steps[0].verification_type == "software_installation"


def test_verification_planner_detects_software_verification():
    planner = VerificationPlanner()
    
    plan = {
        "sub_goal_plans": [
            {
                "sub_goal_id": "sg1",
                "steps": [
                    {"step_number": 1, "action": "Install Flutter"}
                ]
            }
        ]
    }
    
    verification_plan = planner.build_plan(plan, "Install Flutter")
    
    assert verification_plan.steps[0].verification_type == "software_installation"


def test_verification_planner_handles_empty_plan():
    planner = VerificationPlanner()
    
    verification_plan = planner.build_plan({}, None)
    
    assert len(verification_plan.steps) == 0
