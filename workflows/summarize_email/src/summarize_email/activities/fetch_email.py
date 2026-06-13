"""Fetch email content and attachment metadata from the database."""
import logging
from uuid import UUID

from temporalio import activity

from database_client.models.email_v2 import EmailV2
from database_client.models.attachment_v2 import AttachmentV2
from database_client.services import EmailV2Service, AttachmentV2Service

logger = logging.getLogger(__name__)


@activity.defn(name="fetch_email")
async def fetch_email(tenant_id: str, email_id: UUID) -> EmailV2:
    """Fetch the full email record from the database.

    Raises:
        ValueError: If the email is not found
    """
    email_service = EmailV2Service(tenant_id)
    email = await email_service.get_email(email_id)
    if email is None:
        raise ValueError(f"Email {email_id} not found for tenant {tenant_id}")
    logger.info(f"Fetched email {email_id}: subject='{email.subject}'")
    return email


@activity.defn(name="fetch_attachments")
async def fetch_attachments(tenant_id: str, email_id: UUID) -> list[AttachmentV2]:
    """Fetch all supported (PDF/DOCX) attachment metadata for an email."""
    attachment_service = AttachmentV2Service(tenant_id)
    attachments = await attachment_service.get_attachments_by_email(email_id)

    supported = [
        a for a in attachments
        if not a.is_inline and a.file_id is not None and a.content_type in (
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    ]
    skipped = len(attachments) - len(supported)
    logger.info(
        f"Email {email_id}: {len(supported)} supported attachments, {skipped} skipped"
    )
    return supported
