# Email Summarizer — User Guide

## What This Agent Does

The Email Summarizer agent reads emails you send to its mailbox, summarizes the content (including any PDF or DOCX attachments), and replies with a structured summary.

## How to Use It

1. **Send an email** to the agent's configured mailbox address.
2. Attach any PDFs or Word documents (.docx) you want included in the summary.
3. The agent will reply within a few minutes with a structured summary containing:
   - **Overview** — a concise paragraph summarizing the email
   - **Key Points** — the most important facts or decisions
   - **Attachment Highlights** — key findings from each attachment
   - **Action Items** — explicit next steps or requests identified in the email

## Supported Attachment Types

| Type | Supported |
|------|-----------|
| PDF  | Yes       |
| DOCX (Word) | Yes  |
| XLSX (Excel) | No  |
| Images | No      |

Unsupported attachments are skipped; the summary will note how many were skipped.

## Tips

- **Long emails**: The agent handles long bodies — include as much context as you need.
- **Multiple attachments**: All supported attachments are summarized together in a single reply.
- **No attachments**: The agent will still summarize the email body on its own.
- **Forwarded emails**: The agent summarizes the full forwarded thread body.

## Dashboard

View processed email history and summary counts in the Email Summarizer Dashboard.
