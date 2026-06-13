"""Data models for the summarize_email workflow."""
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class AttachmentContent(BaseModel):
    """Processed content of a single attachment."""
    name: str
    content_type: str
    text: Optional[str] = None  # extracted text (DOCX)
    file_id: Optional[UUID] = None  # present for PDF → upload to LLM


class SummaryOutput(BaseModel):
    """Structured output from the LLM summarization call."""
    overview: str = Field(description="2-3 sentence summary of the email and all attachments")
    key_points: list[str] = Field(description="Bullet-point list of key information")
    attachment_highlights: list[str] = Field(
        description="One line per attachment processed; empty if none",
        default_factory=list,
    )
    action_items: list[str] = Field(
        description="Any tasks or requests detected in the email",
        default_factory=list,
    )
