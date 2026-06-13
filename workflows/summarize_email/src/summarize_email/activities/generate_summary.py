"""Generate a combined LLM summary of an email and its attachments."""
import io
import logging
from uuid import UUID

import docx  # python-docx
from temporalio import activity

import summarize_email.prompts as prompts_pkg
from common.llm import get_language_model, MediaItem, MediaType
from common.llm.prompt import prompt_file_loader_v2
from database_client.models.email_v2 import EmailV2
from database_client.models.attachment_v2 import AttachmentV2
from file_client import FileService
from summarize_email.models.workflow_models import SummaryOutput

logger = logging.getLogger(__name__)

_PDF_CONTENT_TYPE = "application/pdf"
_DOCX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


def _extract_docx_text(raw_bytes: bytes) -> str:
    """Extract plain text from DOCX bytes using python-docx."""
    doc = docx.Document(io.BytesIO(raw_bytes))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


@activity.defn(name="generate_combined_summary")
async def generate_combined_summary(
    tenant_id: str,
    agent_id: UUID,
    email: EmailV2,
    attachments: list[AttachmentV2],
) -> SummaryOutput:
    """Generate a single combined summary of the email and all supported attachments."""
    file_service = FileService(tenant_id)
    system_prompt, user_prompts, llm_config = prompt_file_loader_v2(
        "config.json", prompts_pkg
    )
    llm = get_language_model(
        llm_config,
        tenant_id,
        agent_id,
        session_id=activity.info().workflow_id,
    )

    pdf_media_items: list[MediaItem] = []
    docx_texts: list[tuple[str, str]] = []
    skipped_count = 0

    for att in attachments:
        if att.file_id is None:
            skipped_count += 1
            continue

        raw_bytes = await file_service.get_document_bytes(att.file_id)
        if raw_bytes is None:
            logger.warning(f"Could not download attachment {att.name} (file_id={att.file_id})")
            skipped_count += 1
            continue

        if att.content_type == _PDF_CONTENT_TYPE:
            pdf_media_items.append(MediaItem(
                file_name=att.name,
                type=MediaType.PDF,
                data=raw_bytes,
                mime_type="application/pdf",
            ))
            logger.info(f"Prepared PDF attachment: {att.name}")
        elif att.content_type == _DOCX_CONTENT_TYPE:
            try:
                text = _extract_docx_text(raw_bytes)
                docx_texts.append((att.name, text))
                logger.info(f"Extracted DOCX text from: {att.name} ({len(text)} chars)")
            except Exception as exc:
                logger.warning(f"Failed to extract DOCX {att.name}: {exc}")
                skipped_count += 1

    sender = ""
    if email.sender:
        sender = email.sender.address
    elif email.from_:
        sender = email.from_[0].address

    all_media = pdf_media_items
    system_prompt.compile()
    user_prompts["summarize"].compile(
        sender=sender,
        subject=email.subject,
        body=email.body,
        attachment_count=len(attachments),
        docx_texts=docx_texts,
        skipped_count=skipped_count,
        media_items=all_media if all_media else None,
    )

    response = await llm.invoke(
        prompts=[system_prompt, user_prompts["summarize"]],
        llm_config=llm_config,
        response_format=SummaryOutput,
    )
    summary: SummaryOutput = response.message

    if skipped_count > 0:
        summary.attachment_highlights.append(
            f"{skipped_count} attachment(s) skipped (unsupported format)"
        )

    logger.info(
        f"Generated summary for email {email.id}: "
        f"pdf={len(pdf_media_items)}, docx={len(docx_texts)}, skipped={skipped_count}"
    )
    return summary
