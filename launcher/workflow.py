"""Workflow CLI launcher — invoke LangGraph workflows from the command line."""

import uuid

from shared.runtime.workflow_runtime import WorkflowRuntime


async def run_workflow_cli(
    runtime: WorkflowRuntime,
    workflow_name: str,
    user_input: str,
) -> None:
    thread_id = f"cli-{uuid.uuid4().hex[:8]}"

    result = await runtime.run(
        workflow_name=workflow_name,
        user_input=user_input,
        thread_id=thread_id,
    )

    print(result)