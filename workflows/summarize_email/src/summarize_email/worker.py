"""Temporal worker for the email summarizer agent."""
import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from common.config import secrets
from common_activities.temporal import get_secure_data_converter
from common.log_setup.log_setup import setup_logs
from common.metrics.metrics import setup_metrics
from common_activities.workflows.activities.send_email import send_email

from summarize_email.summarize_email_workflow import SummarizeEmailWorkflow
from summarize_email.activities.get_agent import get_agent_by_name
from summarize_email.activities.fetch_email import fetch_email, fetch_attachments
from summarize_email.activities.generate_summary import generate_combined_summary
from summarize_email.activities.save_summary import save_summary
from summarize_email.activities.send_reply import send_reply

TASK_QUEUE = "email-summarizer-tq"


async def main() -> None:
    """Initialize and run the Temporal worker."""
    runtime = setup_logs()
    setup_metrics("email-summarizer")

    client = await Client.connect(
        secrets.TEMPORAL_ENDPOINT,
        namespace=secrets.TEMPORAL_NAMESPACE,
        api_key=secrets.TEMPORAL_API_KEY,
        tls=secrets.TEMPORAL_TLS,
        data_converter=get_secure_data_converter(),
        runtime=runtime,
    )

    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[SummarizeEmailWorkflow],
        activities=[
            get_agent_by_name,
            fetch_email,
            fetch_attachments,
            generate_combined_summary,
            save_summary,
            send_reply,
            send_email,  # from common-activities (used by send_reply)
        ],
    )

    print("Worker listening on task queue: email-summarizer-tq")
    await worker.run()


if __name__ == "__main__":
    print("Starting summarize_email worker...")
    print("Press Ctrl+C to stop")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nWorker stopped")
