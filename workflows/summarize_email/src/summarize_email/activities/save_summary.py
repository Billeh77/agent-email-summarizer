"""Persist a generated summary to the database via SummaryService."""
import json
import logging
from datetime import datetime, timezone
from uuid import UUID

from temporalio import activity

from database_client.services import SummaryService
from database_client.services.document_v2 import DocumentV2Service
from database_client.models.summary import SummaryBase, SummaryType
from database_client.models.document_v2 import DocumentV2Create
from database_client.models.document import DocumentSource
from file_client import FileService, File
from summarize_email.models.workflow_models import SummaryOutput

logger = logging.getLogger(__name__)


@activity.defn(name="save_summary")
async def save_summary(
    tenant_id: str,
    agent_id: UUID,
    email_id: UUID,
    subject: str,
    email_body: str,
    summary: SummaryOutput,
) -> UUID:
    """Persist the summary to the database.

    Creates a document record (backed by the email body in file service) so
    the summary can be linked via doc_id, which the summaries table requires.

    Returns:
        UUID of the created summary record
    """
    # Store email body as a text file so we have a file_id for the document record
    file_service = FileService(tenant_id)
    file_id = await file_service.store_document(
        File(name=f"email-{email_id}.txt", content=email_body)
    )

    # Create a document record that represents this email
    doc_service = DocumentV2Service(tenant_id)
    document = await doc_service.create_document(
        DocumentV2Create(
            name=subject or f"Email {email_id}",
            file_id=file_id,
            timestamp=datetime.now(tz=timezone.utc),
            agent_id=agent_id,
            source=DocumentSource.EMAIL,
            source_id=email_id,
        )
    )
    doc_id = document.id

    # Save the summary linked to the document
    summary_service = SummaryService(tenant_id)
    summary_id = await summary_service.post_summary_to_db(
        SummaryBase(
            doc_id=doc_id,
            summary_type=SummaryType.DETAILED,
            text=json.dumps(summary.model_dump()),
            agent_id=str(agent_id),
        )
    )
    logger.info(f"Saved summary {summary_id} for email {email_id} (doc_id={doc_id})")
    return summary_id
