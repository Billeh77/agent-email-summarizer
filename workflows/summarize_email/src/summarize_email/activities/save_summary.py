"""Persist a generated summary to the database via SummaryService."""
import json
import logging
from uuid import UUID

from temporalio import activity

from database_client.services import SummaryService
from database_client.models.summary import SummaryBase, SummaryType
from summarize_email.models.workflow_models import SummaryOutput

logger = logging.getLogger(__name__)


@activity.defn(name="save_summary")
async def save_summary(
    tenant_id: str,
    agent_id: UUID,
    email_id: UUID,
    summary: SummaryOutput,
) -> UUID:
    """Persist the summary to the database.

    Uses email_id as the doc_id so summaries can be retrieved by email.

    Returns:
        UUID of the created summary record
    """
    summary_service = SummaryService(tenant_id)
    summary_id = await summary_service.post_summary_to_db(
        SummaryBase(
            doc_id=email_id,
            summary_type=SummaryType.DETAILED,
            text=json.dumps(summary.model_dump()),
            agent_id=str(agent_id),
        )
    )
    logger.info(f"Saved summary {summary_id} for email {email_id}")
    return summary_id
