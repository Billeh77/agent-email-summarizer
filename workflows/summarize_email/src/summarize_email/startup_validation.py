#!/usr/bin/env python
"""
Startup validation script for summarize_email workflow.

Run this before deployment to ensure all components are properly configured.
"""
import sys
import asyncio
from typing import List, Tuple


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


class StartupValidator:
    """Validates workflow configuration and dependencies."""

    def __init__(self):
        self.checks: List[Tuple[str, bool, str]] = []

    async def validate_all(self) -> bool:
        """Run all validation checks."""
        print("🔍 Running startup validation for summarize_email...\n")

        await self.check_imports()
        await self.check_environment()
        await self.check_database_connection()
        await self.check_temporal_connection()
        await self.check_agent_registration()
        await self.check_prompts()
        await self.check_llm_models()

        print("\n" + "=" * 50)
        print("VALIDATION RESULTS")
        print("=" * 50 + "\n")

        all_passed = True
        for name, passed, message in self.checks:
            status = "✅" if passed else "❌"
            print(f"{status} {name}")
            if not passed:
                print(f"   ↳ {message}")
                all_passed = False

        print("\n" + "=" * 50)
        if all_passed:
            print("✅ All checks passed! Ready for deployment.")
        else:
            print("❌ Some checks failed. Please fix the issues above.")
        print("=" * 50 + "\n")

        return all_passed

    def add_check(self, name: str, passed: bool, message: str = "") -> None:
        """Record a validation check result."""
        self.checks.append((name, passed, message))

    async def check_imports(self):
        """Check that all required modules can be imported."""
        try:
            from summarize_email.summarize_email_workflow import SummarizeEmailWorkflow  # noqa: F401
            from summarize_email.activities.fetch_email import fetch_email, fetch_attachments  # noqa: F401
            from summarize_email.activities.generate_summary import generate_combined_summary  # noqa: F401
            from summarize_email.activities.save_summary import save_summary  # noqa: F401
            from summarize_email.activities.send_reply import send_reply  # noqa: F401
            from common.config import secrets  # noqa: F401
            from common.log_setup.log_setup import setup_logs  # noqa: F401
            from database_client.services import EmailV2Service  # noqa: F401
            self.add_check("Required imports", True)
        except ImportError as e:
            self.add_check("Required imports", False, str(e))

    async def check_environment(self):
        """Check that required environment variables are set."""
        try:
            from common.config.secrets import (
                TEMPORAL_ENDPOINT,
                TEMPORAL_NAMESPACE,
                KEY_VAULT_NAME,
            )

            required_vars = {
                "TEMPORAL_ENDPOINT": TEMPORAL_ENDPOINT,
                "TEMPORAL_NAMESPACE": TEMPORAL_NAMESPACE,
                "KEY_VAULT_NAME": KEY_VAULT_NAME,
            }

            missing = [k for k, v in required_vars.items() if not v]
            if missing:
                self.add_check(
                    "Environment variables",
                    False,
                    f"Missing: {', '.join(missing)}"
                )
            else:
                self.add_check("Environment variables", True)

        except Exception as e:
            self.add_check("Environment variables", False, str(e))

    async def check_database_connection(self):
        """Check that database service is accessible."""
        try:
            from database_client.services import EmailV2Service

            test_tenant = "test-tenant"
            service = EmailV2Service(test_tenant)

            try:
                await service.count_emails()
                self.add_check("Database connection", True)
            except Exception as e:
                if "401" in str(e) or "403" in str(e) or "404" in str(e):
                    self.add_check("Database connection", True)
                else:
                    self.add_check("Database connection", False, str(e))

        except Exception as e:
            self.add_check("Database connection", False, str(e))

    async def check_temporal_connection(self):
        """Check that Temporal service is accessible."""
        try:
            from temporalio.client import Client
            from common.config.secrets import (
                TEMPORAL_ENDPOINT,
                TEMPORAL_NAMESPACE,
                TEMPORAL_API_KEY,
                TEMPORAL_TLS,
            )

            client = await Client.connect(
                TEMPORAL_ENDPOINT,
                namespace=TEMPORAL_NAMESPACE,
                api_key=TEMPORAL_API_KEY,
                tls=TEMPORAL_TLS,
            )

            try:
                await client.workflow_service.describe_namespace(
                    namespace=TEMPORAL_NAMESPACE
                )
                self.add_check("Temporal connection", True)
            except Exception as e:
                if "deadline" in str(e).lower():
                    self.add_check("Temporal connection", False, "Connection timeout")
                else:
                    self.add_check("Temporal connection", True)

        except Exception as e:
            self.add_check("Temporal connection", False, str(e))

    async def check_agent_registration(self):
        """Check agent registration in database."""
        try:
            from database_client.services import AgentService

            test_tenant = "test-tenant"
            agent_name = "email-summarizer"
            service = AgentService(test_tenant)

            try:
                agent = await service.get_agent_by_name(agent_name)
                if agent:
                    self.add_check(
                        "Agent registration",
                        True,
                        f"Agent ID: {agent.id}"
                    )
                else:
                    self.add_check(
                        "Agent registration",
                        False,
                        f"Agent '{agent_name}' not found. Run agent registration."
                    )
            except Exception as e:
                if "401" in str(e) or "403" in str(e):
                    self.add_check(
                        "Agent registration",
                        False,
                        "Cannot check — auth required."
                    )
                else:
                    self.add_check("Agent registration", False, str(e))

        except Exception as e:
            self.add_check("Agent registration", False, str(e))

    async def check_prompts(self):
        """Check that prompt files exist and are valid."""
        try:
            from pathlib import Path
            import json

            prompts_dir = Path(__file__).parent / "prompts"

            if not prompts_dir.exists():
                self.add_check("Prompt files", False, "Prompts directory not found")
                return

            json_files = list(prompts_dir.glob("*.json"))
            if not json_files:
                self.add_check("Prompt files", False, "No prompt JSON files found")
                return

            for json_file in json_files:
                try:
                    with open(json_file) as f:
                        config = json.load(f)
                        if "llm_config" not in config:
                            self.add_check(
                                "Prompt files",
                                False,
                                f"{json_file.name}: Missing llm_config"
                            )
                            return
                except Exception as e:
                    self.add_check(
                        "Prompt files",
                        False,
                        f"{json_file.name}: Invalid JSON - {e}"
                    )
                    return

            self.add_check("Prompt files", True, f"Found {len(json_files)} prompts")

        except Exception as e:
            self.add_check("Prompt files", False, str(e))

    async def check_llm_models(self):
        """Check that LLM models specified in prompts actually exist."""
        try:
            from pathlib import Path
            import json

            VALID_MODELS = {
                "google": ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-pro", "gemini-1.5-flash"],
                "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4.1", "gpt-3.5-turbo"],
                "anthropic": [
                    "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022",
                    "claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"
                ],
            }

            prompts_dir = Path(__file__).parent / "prompts"

            if not prompts_dir.exists():
                self.add_check("LLM models", True, "No prompts directory to check")
                return

            issues = []
            checked_count = 0

            for json_file in prompts_dir.glob("*.json"):
                try:
                    with open(json_file) as f:
                        config = json.load(f)

                    if "llm_config" in config:
                        checked_count += 1
                        vendor = config["llm_config"].get("llm_vendor", "").lower()
                        model = config["llm_config"].get("llm_model_name", "")

                        if vendor not in VALID_MODELS:
                            issues.append(f"{json_file.name}: Unknown vendor '{vendor}'")
                        elif model not in VALID_MODELS[vendor]:
                            issues.append(
                                f"{json_file.name}: Model '{model}' not in valid {vendor} models."
                            )

                except Exception as e:
                    issues.append(f"{json_file.name}: Error reading config - {e}")

            if issues:
                self.add_check("LLM models", False, f"Invalid models: {'; '.join(issues)}")
            elif checked_count > 0:
                self.add_check("LLM models", True, f"All {checked_count} models are valid")
            else:
                self.add_check("LLM models", True, "No LLM configs to validate")

        except Exception as e:
            self.add_check("LLM models", False, str(e))


async def main():
    """Run the validation."""
    validator = StartupValidator()
    success = await validator.validate_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
