"""Email summarizer workflow — triggered by the multi-agent-poller."""
import asyncio
import logging
from datetime import timedelta
from typing import cast

from temporalio import common, workflow

from common_activities.workflows.models.workflow_invocation import (
    Invocation,
    InvocationType,
    EmailTrigger,
)

with workflow.unsafe.imports_passed_through():
    from summarize_email.activities.get_agent import get_agent_by_name
    from summarize_email.activities.fetch_email import fetch_email, fetch_attachments
    from summarize_email.activities.generate_summary import generate_combined_summary
    from summarize_email.activities.save_summary import save_summary
    from summarize_email.activities.send_reply import send_reply

logger = logging.getLogger(__name__)

_RETRY_DEFAULT = common.RetryPolicy(
    initial_interval=timedelta(seconds=2),
    maximum_attempts=3,
)
_RETRY_SAVE = common.RetryPolicy(
    initial_interval=timedelta(seconds=5),
    maximum_attempts=5,
)


@workflow.defn
class SummarizeEmailWorkflow:
    """Summarizes incoming emails and attachments, then replies to the sender."""

    @workflow.run
    async def run(self, invocation: Invocation) -> str:
        workflow_id = workflow.info().workflow_id
        start_time = workflow.now()
        logger.info(f"SummarizeEmailWorkflow started workflow_id={workflow_id}")

        if invocation.type != InvocationType.EMAIL:
            logger.info(f"Skipping non-email invocation: {invocation.type}")
            return "Skipped: Only processes EMAIL triggers"

        email_trigger = cast(EmailTrigger, invocation.trigger)
        email_id = email_trigger.email_id
        tenant_id = invocation.tenant_id

        # Resolve agent_id — prefer what the poller provides; fall back to DB lookup
        agent_id = invocation.agent_id
        if agent_id is None:
            agent_id = await workflow.execute_activity(
                get_agent_by_name,
                args=[tenant_id, "agent-email-summarizer"],
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=common.RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_attempts=3,
                ),
            )

        # Fetch email and attachment metadata in parallel
        email, attachments = await asyncio.gather(
            workflow.execute_activity(
                fetch_email,
                args=[tenant_id, email_id],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=_RETRY_DEFAULT,
            ),
            workflow.execute_activity(
                fetch_attachments,
                args=[tenant_id, email_id],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=common.RetryPolicy(
                    initial_interval=timedelta(seconds=5),
                    maximum_attempts=2,
                ),
            ),
        )

        # Generate combined LLM summary
        summary = await workflow.execute_activity(
            generate_combined_summary,
            args=[tenant_id, agent_id, email, attachments],
            start_to_close_timeout=timedelta(minutes=3),
            retry_policy=_RETRY_DEFAULT,
        )

        # Persist summary
        await workflow.execute_activity(
            save_summary,
            args=[tenant_id, agent_id, email_id, email.subject, email.body, summary],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=_RETRY_SAVE,
        )

        # Reply to sender
        await workflow.execute_activity(
            send_reply,
            args=[tenant_id, agent_id, email_trigger.account, email_id, email.subject, summary],
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=_RETRY_DEFAULT,
        )

        duration_ms = round((workflow.now() - start_time).total_seconds() * 1000)
        logger.info(f"SummarizeEmailWorkflow completed email={email_id} duration_ms={duration_ms}")
        return f"Completed: summarized and replied to email {email_id}"
