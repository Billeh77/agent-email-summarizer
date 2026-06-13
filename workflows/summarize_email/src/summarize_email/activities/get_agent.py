"""Get agent by name from database."""
from uuid import UUID
from temporalio import activity

from database_client.services import AgentService

AGENT_NAME = "email-summarizer"


@activity.defn(name="get_agent_by_name")
async def get_agent_by_name(tenant_id: str, agent_name: str) -> UUID:
    """
    Look up agent by name and return its ID.

    Prefer invocation.agent_id when the workflow invocation provides it. Use this
    lookup only as a compatibility fallback for invocations that do not carry an
    agent_id. The agent_id is needed for LLM session tracking and metrics
    attribution.

    Args:
        tenant_id: Tenant ID
        agent_name: Name of the agent to look up (e.g., "agent-email-summarizer")

    Returns:
        Agent UUID

    Raises:
        ValueError: If agent not found in database

    Example:
        agent_id = await workflow.execute_activity(
            get_agent_by_name,
            args=[tenant_id, "agent-email-summarizer"],
            start_to_close_timeout=timedelta(seconds=10),
        )
    """
    agent_service = AgentService(tenant_id)
    agent = await agent_service.get_agent_by_name(agent_name)

    if not agent:
        raise ValueError(f"Agent '{agent_name}' not found in database")

    return agent.id
