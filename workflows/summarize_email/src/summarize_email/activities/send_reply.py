"""Send a structured summary reply to the original email sender."""
import logging
from uuid import UUID

from temporalio import activity

from common_activities.models.account import Account
from common_activities.workflows.activities.send_email import send_email, SendEmailRequest
from summarize_email.models.workflow_models import SummaryOutput

logger = logging.getLogger(__name__)


def _build_reply_body(subject: str, summary: SummaryOutput) -> str:
    """Assemble a structured Markdown reply body from the summary."""
    lines: list[str] = [
        "Here is a summary of your email and attachments:",
        "",
        "**Overview**",
        summary.overview,
    ]

    if summary.key_points:
        lines += ["", "**Key Points**"]
        lines += [f"- {pt}" for pt in summary.key_points]

    if summary.attachment_highlights:
        lines += ["", "**Attachment Highlights**"]
        lines += [f"- {h}" for h in summary.attachment_highlights]

    if summary.action_items:
        lines += ["", "**Action Items**"]
        lines += [f"- {ai}" for ai in summary.action_items]

    return "\n".join(lines)


@activity.defn(name="send_reply")
async def send_reply(
    tenant_id: str,
    agent_id: UUID,
    account: Account,
    email_id: UUID,
    subject: str,
    summary: SummaryOutput,
) -> None:
    """Send a reply to the original email with the generated summary."""
    body = _build_reply_body(subject, summary)

    await send_email(SendEmailRequest(
        tenant_id=tenant_id,
        inbox_user=account,
        subject=f"Re: {subject}",
        body=body,
        in_reply_to_id=email_id,
        use_v2=True,
        include_previous_email=False,
        on_behalf_of_agent_id=agent_id,
    ))
    logger.info(f"Sent summary reply for email {email_id}")
