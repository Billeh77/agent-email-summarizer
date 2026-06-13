"""
Workflow runner for manual testing and development.

In production, workflows are triggered by the multi-agent-poller email event.
This runner is only for local development/testing.
"""
from typing import Dict, Any
from uuid import uuid4
from datetime import datetime

from temporalio import common
from temporalio.client import Client

from common.config.secrets import (
    TEMPORAL_API_KEY,
    TEMPORAL_ENDPOINT,
    TEMPORAL_NAMESPACE,
    TEMPORAL_TLS,
)
from common_activities.temporal import get_secure_data_converter
from common_activities.workflows.models.workflow_invocation import (
    Invocation, InvocationType, EmailTrigger,
)
from common_activities.models.account import Account


async def start_workflow(request: Dict[str, Any]):
    """Start the workflow for testing."""
    client = await Client.connect(
        TEMPORAL_ENDPOINT,
        namespace=TEMPORAL_NAMESPACE,
        api_key=TEMPORAL_API_KEY,
        tls=TEMPORAL_TLS,
        data_converter=get_secure_data_converter(),
    )

    wid = f"summarize_email-test-{uuid4().hex[:8]}"
    print(f"Starting workflow {wid}")
    print(f"Input: {request}")

    handle = await client.start_workflow(
        "SummarizeEmailWorkflow",
        request,
        id=wid,
        task_queue="email-summarizer-tq",
        id_reuse_policy=common.WorkflowIDReusePolicy.ALLOW_DUPLICATE_FAILED_ONLY,
    )

    print("Workflow started. Waiting for result...")

    try:
        result = await handle.result()
        print("✓ Workflow completed successfully")
        print(f"Result: {result}")
        return result
    except Exception as e:
        print(f"✗ Workflow failed: {e}")
        raise


def create_test_request() -> Invocation:
    """Create a test Invocation for local development."""
    return Invocation(
        tenant_id="test-tenant",
        type=InvocationType.EMAIL,
        trigger=EmailTrigger(
            type="email",
            email_id=uuid4(),
            account=Account(
                auth0_id="test|account",
                system_account_id=str(uuid4()),
            ),
        ),
        agent_id=None,
        timestamp=datetime.utcnow(),
    )
