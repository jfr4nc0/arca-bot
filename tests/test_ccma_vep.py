#!/usr/bin/env python3
"""
Test for the new VEP generation step in CCMA workflow
"""

import os
import sys

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workflows.ccma_workflow import CCMAWorkflow


def test_ccma_workflow_steps():
    """Test that the CCMA workflow includes the new VEP generation step."""
    workflow = CCMAWorkflow()

    # Check that all expected steps are present
    expected_steps = [
        "initialize_browser",
        "afip_login",
        "open_ccma_window",
        "calculate_debt",
        "handle_debt_window",
        "generate_vep",
    ]

    for step in expected_steps:
        assert step in workflow.steps, f"Step {step} not found in workflow"
        print(f"✓ Step '{step}' found in workflow")

    # Check dependencies
    assert (
        "handle_debt_window" in workflow.steps["generate_vep"].depends_on
    ), "generate_vep step should depend on handle_debt_window"
    print("✓ Dependency correctly set: generate_vep depends on handle_debt_window")

    # Check execution order
    execution_order = workflow.get_step_execution_order()
    assert (
        execution_order[-1] == "generate_vep"
    ), "generate_vep should be the last step in execution order"
    print("✓ Execution order correctly includes generate_vep as last step")

    print("\nAll tests passed!")


if __name__ == "__main__":
    test_ccma_workflow_steps()
