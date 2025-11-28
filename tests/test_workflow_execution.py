#!/usr/bin/env python3
"""
Test script to verify CCMA workflow execution order
"""

import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workflows.ccma_workflow import CCMAWorkflow


def main():
    print("Testing CCMA workflow execution order...")

    # Create a workflow instance
    workflow = CCMAWorkflow()

    # Get execution order
    execution_order = workflow.get_step_execution_order()

    print("\nExecution Order:")
    for i, step_name in enumerate(execution_order, 1):
        print(f"  {i}. {step_name}")

        # Check dependencies for each step
        step = workflow.steps[step_name]
        if step.depends_on:
            print(f"     Depends on: {', '.join(step.depends_on)}")

    # Verify that generate_vep is the last step
    if execution_order[-1] == "generate_vep":
        print("\n✓ 'generate_vep' is correctly positioned as the last step")
    else:
        print("\n✗ 'generate_vep' is NOT the last step")
        return False

    # Verify that handle_debt_window comes before generate_vep
    handle_debt_window_index = (
        execution_order.index("handle_debt_window")
        if "handle_debt_window" in execution_order
        else -1
    )
    generate_vep_index = (
        execution_order.index("generate_vep")
        if "generate_vep" in execution_order
        else -1
    )

    if (
        handle_debt_window_index != -1
        and generate_vep_index != -1
        and handle_debt_window_index < generate_vep_index
    ):
        print("✓ 'handle_debt_window' correctly comes before 'generate_vep'")
    else:
        print("✗ 'handle_debt_window' does NOT correctly come before 'generate_vep'")
        return False

    print("\nAll checks passed! ✓")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
