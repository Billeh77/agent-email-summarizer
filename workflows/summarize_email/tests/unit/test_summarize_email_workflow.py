"""Unit tests for the SummarizeEmailWorkflow."""
import pytest
from datetime import datetime, timezone
from uuid import uuid4, UUID

from temporalio.client import WorkflowFailureError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker, UnsandboxedWorkflowRunner
from temporalio import activity

from summarize_email.summarize_email_workflow import SummarizeEmailWorkflow
from summarize_email.models.workflow_models import SummaryOutput
from common_activities.workflows.models.workflow_invocation import (
    Invocation,
    InvocationType,
    EmailTrigger,
    ReportTrigger,
)
from common_activities.models.account import Account

pytestmark = pytest.mark.unit

_TENANT = "test-tenant"
_ACCOUNT = Account(auth0_id="waad|test", system_account_id=str(uuid4()))

_SUMMARY = SummaryOutput(
    overview="This is a test email overview.",
    key_points=["Point A", "Point B"],
    attachment_highlights=["Doc.pdf: contract terms"],
    action_items=["Reply by Friday"],
)


def _make_email_invocation(
    email_id: UUID | None = None,
    agent_id: UUID | None = None,
) -> Invocation:
    return Invocation(
        tenant_id=_TENANT,
        type=InvocationType.EMAIL,
        trigger=EmailTrigger(
            type="email",
            email_id=email_id or uuid4(),
            account=_ACCOUNT,
        ),
        agent_id=agent_id or uuid4(),
        timestamp=datetime.now(tz=timezone.utc),
    )


def _make_email_v2(email_id: UUID, subject: str = "Test Subject"):
    """Return a minimal EmailV2 Pydantic model instance."""
    from database_client.models.email_v2 import EmailV2
    from database_client.models import EmailAddress

    now = datetime.now(tz=timezone.utc)
    return EmailV2(
        id=email_id,
        provider_msg_id="test-provider-id",
        internet_msg_id="test-internet-id",
        subject=subject,
        body="Email body text",
        sender=EmailAddress(address="sender@example.com"),
        from_=[EmailAddress(address="sender@example.com")],
        to_recipients=[],
        received_at=now,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_workflow_processes_email_successfully():
    """Happy path: workflow fetches email, summarizes, saves, and replies."""
    email_id = uuid4()
    invocation = _make_email_invocation(email_id=email_id)

    @activity.defn(name="get_agent_by_name")
    async def mock_get_agent(tenant_id: str, agent_name: str) -> UUID:
        raise AssertionError("should prefer invocation.agent_id")

    @activity.defn(name="fetch_email")
    async def mock_fetch_email(tenant_id: str, eid: UUID):
        return _make_email_v2(eid)

    @activity.defn(name="fetch_attachments")
    async def mock_fetch_attachments(tenant_id: str, eid: UUID) -> list:
        return []

    @activity.defn(name="generate_combined_summary")
    async def mock_generate(tenant_id, agent_id, email, attachments) -> SummaryOutput:
        return _SUMMARY

    @activity.defn(name="save_summary")
    async def mock_save(tenant_id, agent_id, eid, subject, body, summary) -> UUID:
        return uuid4()

    @activity.defn(name="send_reply")
    async def mock_reply(tenant_id, agent_id, account, eid, subject, summary) -> None:
        return None

    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue="test",
            workflows=[SummarizeEmailWorkflow],
            activities=[
                mock_get_agent,
                mock_fetch_email,
                mock_fetch_attachments,
                mock_generate,
                mock_save,
                mock_reply,
            ],
            workflow_runner=UnsandboxedWorkflowRunner(),
        ):
            result = await env.client.execute_workflow(
                SummarizeEmailWorkflow.run,
                invocation,
                id=f"test-{uuid4()}",
                task_queue="test",
            )

    assert "Completed" in result
    assert str(email_id) in result


@pytest.mark.asyncio
async def test_workflow_skips_non_email_invocation():
    """Workflow should return skip message for non-email triggers."""

    @activity.defn(name="get_agent_by_name")
    async def mock_get_agent(tenant_id: str, agent_name: str) -> UUID:
        return uuid4()

    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue="test",
            workflows=[SummarizeEmailWorkflow],
            activities=[mock_get_agent],
            workflow_runner=UnsandboxedWorkflowRunner(),
        ):
            invocation = Invocation(
                tenant_id=_TENANT,
                type=InvocationType.SCHEDULED,
                trigger=ReportTrigger(
                    type="scheduled",
                    account=_ACCOUNT,
                    recipients=[],
                ),
                agent_id=uuid4(),
                timestamp=datetime.now(tz=timezone.utc),
            )
            result = await env.client.execute_workflow(
                SummarizeEmailWorkflow.run,
                invocation,
                id=f"test-{uuid4()}",
                task_queue="test",
            )

    assert result == "Skipped: Only processes EMAIL triggers"


@pytest.mark.asyncio
async def test_workflow_falls_back_to_agent_lookup_when_no_agent_id():
    """When invocation has no agent_id, workflow should call get_agent_by_name."""
    looked_up = False
    resolved_agent_id = uuid4()
    email_id = uuid4()

    @activity.defn(name="get_agent_by_name")
    async def mock_get_agent(tenant_id: str, agent_name: str) -> UUID:
        nonlocal looked_up
        looked_up = True
        return resolved_agent_id

    @activity.defn(name="fetch_email")
    async def mock_fetch_email(tenant_id: str, eid: UUID):
        return _make_email_v2(eid)

    @activity.defn(name="fetch_attachments")
    async def mock_fetch_attachments(tenant_id: str, eid: UUID) -> list:
        return []

    @activity.defn(name="generate_combined_summary")
    async def mock_generate(tenant_id, agent_id, email, attachments) -> SummaryOutput:
        return _SUMMARY

    @activity.defn(name="save_summary")
    async def mock_save(tenant_id, agent_id, eid, subject, body, summary) -> UUID:
        return uuid4()

    @activity.defn(name="send_reply")
    async def mock_reply(tenant_id, agent_id, account, eid, subject, summary) -> None:
        return None

    invocation = Invocation(
        tenant_id=_TENANT,
        type=InvocationType.EMAIL,
        trigger=EmailTrigger(type="email", email_id=email_id, account=_ACCOUNT),
        agent_id=None,  # force lookup
        timestamp=datetime.now(tz=timezone.utc),
    )

    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue="test",
            workflows=[SummarizeEmailWorkflow],
            activities=[
                mock_get_agent,
                mock_fetch_email,
                mock_fetch_attachments,
                mock_generate,
                mock_save,
                mock_reply,
            ],
            workflow_runner=UnsandboxedWorkflowRunner(),
        ):
            result = await env.client.execute_workflow(
                SummarizeEmailWorkflow.run,
                invocation,
                id=f"test-{uuid4()}",
                task_queue="test",
            )

    assert looked_up is True
    assert "Completed" in result


@pytest.mark.asyncio
async def test_workflow_fails_when_agent_lookup_fails():
    """Workflow should propagate failure when agent lookup raises."""

    @activity.defn(name="get_agent_by_name")
    async def mock_get_agent(tenant_id: str, agent_name: str) -> UUID:
        raise ValueError("Agent not found")

    invocation = Invocation(
        tenant_id=_TENANT,
        type=InvocationType.EMAIL,
        trigger=EmailTrigger(type="email", email_id=uuid4(), account=_ACCOUNT),
        agent_id=None,
        timestamp=datetime.now(tz=timezone.utc),
    )

    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue="test",
            workflows=[SummarizeEmailWorkflow],
            activities=[mock_get_agent],
            workflow_runner=UnsandboxedWorkflowRunner(),
        ):
            with pytest.raises(WorkflowFailureError) as exc_info:
                await env.client.execute_workflow(
                    SummarizeEmailWorkflow.run,
                    invocation,
                    id=f"test-{uuid4()}",
                    task_queue="test",
                )

    cause = exc_info.value
    messages: list[str] = []
    while cause is not None:
        messages.append(str(cause))
        cause = getattr(cause, "cause", None)
    assert any("Agent not found" in m for m in messages)
