"""
Pytest configuration and shared fixtures for workflow tests.

CRITICAL: This file includes module-level Azure Key Vault mocking to prevent
test hangs. The mocks MUST be set up before any imports that use common.config.secrets.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os
from pathlib import Path
# NOTE: pydantic SecretStr import moved after Azure mocks to prevent hangs

# Set environment variables BEFORE any imports that might use Azure Key Vault
os.environ.setdefault("AZURE_CLIENT_ID", "mock-azure-client-id")
os.environ.setdefault("KEY_VAULT_NAME", "mock-vault")
os.environ.setdefault("DB_SERVICE_DOMAIN", "localhost:8000")
os.environ.setdefault("FILE_DOMAIN", "localhost:8002")
os.environ.setdefault("VECTORDB_DOMAIN", "localhost:8003")
os.environ.setdefault("TOKEN_BROKER_DOMAIN", "localhost:8001")
os.environ.setdefault("URL_SCHEME", "http")
os.environ.setdefault("TEMPORAL_ENDPOINT", "localhost:7233")
os.environ.setdefault("TEMPORAL_API_KEY", "")
os.environ.setdefault("TEMPORAL_NAMESPACE", "default")
os.environ.setdefault("TEMPORAL_TLS", "False")
os.environ.setdefault("DB_APP_ID", "mock-db-app-id")
os.environ.setdefault("FILE_APP_ID", "mock-file-app-id")
os.environ.setdefault("HOME_TENANT", "mock-tenant-id")

# Add the src directory to Python path
src_dir = Path(__file__).parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# Mock Azure Key Vault and Azure Identity at module level
_mock_secret_client_patcher = patch("azure.keyvault.secrets.SecretClient")
_mock_credential_patcher = patch("azure.identity.DefaultAzureCredential")

_mock_secret_client = _mock_secret_client_patcher.start()
_mock_credential = _mock_credential_patcher.start()

# Configure the mocks
mock_secret_instance = MagicMock()
mock_secret_instance.get_secret.return_value.value = "mock-secret-value"
_mock_secret_client.return_value = mock_secret_instance

mock_credential_instance = MagicMock()
mock_credential_instance.get_token.return_value.token = "mock-token"
_mock_credential.return_value = mock_credential_instance

# Import pydantic SecretStr AFTER Azure mocks are set up to prevent connection attempts
from pydantic import SecretStr  # noqa: E402


def pytest_collection_modifyitems(config, items):
    """
    Automatically add pytest.mark.unit to all tests in tests/unit/ directory.

    This ensures 'make test-cov' (which runs 'pytest -m unit') includes all unit tests
    without requiring developers to manually add the decorator to every test.
    """
    for item in items:
        # Get the test file path relative to the tests directory
        test_path = Path(item.fspath).relative_to(Path(item.fspath).parent.parent)

        # If test is in tests/unit/, add the unit marker
        if "unit" in test_path.parts:
            item.add_marker(pytest.mark.unit)


@pytest.fixture(autouse=True, scope="function")
def mock_azure_secrets(monkeypatch):
    """Mock Azure Key Vault secrets to prevent connection attempts in unit tests."""
    try:
        import common.config.secrets as secrets_module
    except ImportError:
        if "common.config.secrets" in sys.modules:
            secrets_module = sys.modules["common.config.secrets"]
            if isinstance(secrets_module, MagicMock):
                return
        else:
            return

    # If _secrets is already initialized, patch its methods
    if hasattr(secrets_module, "_secrets"):
        secrets_module._secrets._get_secret = MagicMock(
            return_value="mock-secret-value"
        )

        def mock_get_config_value(key: str, default: str | None = None) -> str:
            env_var = key.upper().replace("-", "_")
            if env_var in os.environ:
                return os.environ[env_var]
            return "mock-config-value"

        secrets_module._secrets._get_config_value = mock_get_config_value

        if (
            not hasattr(secrets_module._secrets, "OPENAI_API_KEY")
            or secrets_module._secrets.OPENAI_API_KEY is None
        ):
            secrets_module._secrets.OPENAI_API_KEY = SecretStr("mock-api-key")


@pytest.fixture(autouse=True, scope="function")
def mock_httpx_client():
    """Mock httpx.AsyncClient to prevent actual HTTP requests in tests."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_instance.get = AsyncMock()
        mock_instance.post = AsyncMock()
        mock_instance.put = AsyncMock()
        mock_instance.patch = AsyncMock()
        mock_instance.delete = AsyncMock()
        mock_client.return_value = mock_instance
        yield mock_instance


# Workflow-specific fixtures below this line

@pytest.fixture
def sample_request():
    """Fixture providing a sample email invocation trigger."""
    from uuid import uuid4
    from datetime import datetime
    from common_activities.workflows.models.workflow_invocation import (
        Invocation, InvocationType, EmailTrigger,
    )
    from common_activities.models.account import Account
    return Invocation(
        tenant_id="test-tenant-123",
        type=InvocationType.EMAIL,
        trigger=EmailTrigger(
            type="email",
            email_id=uuid4(),
            account=Account(auth0_id="waad|test", system_account_id=str(uuid4())),
        ),
        agent_id=uuid4(),
        timestamp=datetime.utcnow(),
    )


@pytest.fixture
def sample_response():
    """Fixture providing a sample SummaryOutput."""
    from summarize_email.models.workflow_models import SummaryOutput
    return SummaryOutput(
        overview="Test overview.",
        key_points=["Point A"],
        attachment_highlights=[],
        action_items=[],
    )


@pytest.fixture
def mock_llm_service():
    """Fixture providing a mocked LLM service."""
    mock_llm = AsyncMock()
    mock_response = MagicMock()
    mock_llm.invoke = AsyncMock(return_value=mock_response)
    return mock_llm


@pytest.fixture
def mock_prompt_components():
    """Fixture providing mocked prompt components."""
    mock_system_prompt = MagicMock()
    mock_system_prompt.compile = MagicMock()

    mock_user_prompt = MagicMock()
    mock_user_prompt.compile = MagicMock()

    mock_llm_config = {"model": "test-model", "temperature": 0.7}

    return {
        "system_prompt": mock_system_prompt,
        "user_prompts": {"subject_prompt": mock_user_prompt},
        "llm_config": mock_llm_config
    }
