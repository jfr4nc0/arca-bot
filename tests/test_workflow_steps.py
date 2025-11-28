#!/usr/bin/env python3
"""
Simple test to verify CCMA workflow steps
"""

import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workflows.ccma_workflow import CCMAWorkflow


def main():
    print("Testing CCMA workflow steps...")

    # Create a workflow instance
    workflow = CCMAWorkflow()

    # List all steps
    print("\nWorkflow Steps:")
    for step_name, step in workflow.steps.items():
        print(f"  - {step_name}: {step.description}")
        if step.depends_on:
            print(f"    Depends on: {', '.join(step.depends_on)}")

    # Check execution order
    print("\nExecution Order:")
    execution_order = workflow.get_step_execution_order()
    for i, step_name in enumerate(execution_order, 1):
        print(f"  {i}. {step_name}")

    # Verify our new step is included
    if "generate_vep" in workflow.steps:
        print("\n✓ New 'generate_vep' step found in workflow")
    else:
        print("\n✗ New 'generate_vep' step NOT found in workflow")
        return False

    # Verify dependencies
    generate_vep_step = workflow.steps["generate_vep"]
    if "handle_debt_window" in generate_vep_step.depends_on:
        print("✓ 'generate_vep' correctly depends on 'handle_debt_window'")
    else:
        print("✗ 'generate_vep' does not depend on 'handle_debt_window'")
        return False

    # Verify position in execution order
    if execution_order[-1] == "generate_vep":
        print("✓ 'generate_vep' is correctly positioned as the last step")
    else:
        print("✗ 'generate_vep' is not the last step in execution order")
        return False

    print("\nAll checks passed! ✓")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
