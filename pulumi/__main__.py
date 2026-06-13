"""Email Summarizer infrastructure."""

import os
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from pulumi_azure_native import appconfiguration
import pulumi
import pulumi_azuread as azuread
from pulumi_random import RandomUuid
from pulumi_azure_native import authorization
from pulumi_azure_native import keyvault
from pulumi_azure_native import web
from pulumi_azure_native import monitor
from pulumi_azure_native import network
import pulumi_azure as azure

config = pulumi.Config()
stack = pulumi.get_stack()
ORG = "organization"

# Stack references to platform services
# =====================================
# Available service stacks (use these exact names):
#   - arata-ai           : Core infrastructure
#   - database-service   : Database API (multi-tenant PostgreSQL)
#   - token-broker       : Service-to-service authentication
#   - file-service       : File storage API (blob storage)
#   - vectordb           : Vector database API (embeddings, RAG)
#   - markdown           : Document conversion API
#
# To add a service manually:
#   1. Add stack reference: service_stack = pulumi.StackReference(f"{ORG}/service-name/{stack}")
#   2. Get app ID: service_app_id = service_stack.get_output("app-id")
#   3. Add scopes to api_access dictionary below
parent_stack = pulumi.StackReference(f"{ORG}/arata-ai/{stack}")
db_stack = pulumi.StackReference(f"{ORG}/database-service/{stack}")
token_broker_stack = pulumi.StackReference(f"{ORG}/token-broker/{stack}")
file_stack = pulumi.StackReference(f"{ORG}/file-service/{stack}")



vnet_id = parent_stack.get_output("vnet-id")
webapp_subnet_id = parent_stack.get_output("webapp-subnet-id")
default_subnet_id = parent_stack.get_output("default-subnet-id")
appgw_subnet_id = parent_stack.get_output("appgw-subnet-id")
webapp_dns_zone_id = parent_stack.get_output("webapp-dns-zone-id")
app_config_name = parent_stack.get_output("app-config-name")

BASE_NAME = "email-summarizer"

# App Configuration settings
APP_NAME = "email-summarizer"
APP_PATH = "/agents/email-summarizer"
APP_PRIORITY = 101
APP_REWRITE = "false"

client_config = authorization.get_client_config()
subscription_id = client_config.subscription_id

common_tags = parent_stack.get_output("tags")


# Helper method for consistent naming
def get_name(prefix, postfix=None):
    if postfix:
        return f"{prefix}-{BASE_NAME}-{stack}-{postfix}"
    else:
        return f"{prefix}-{BASE_NAME}-{stack}"


# Helper method to find an app role ID by its value
def find_app_role_id(app, role_value: str):
    for r in app.app_roles or []:
        if r.value == role_value and r.enabled:
            return r.id
    raise Exception(f"App role '{role_value}' not found/enabled on API {app}.")


resource_group_name = parent_stack.get_output("rg-name")
managed_identity_id = parent_stack.get_output("mi-principal-id")
managed_identity_client_id = parent_stack.get_output("mi-client-id")
acr = parent_stack.get_output("acr-url")
vault_name = parent_stack.get_output("vault-name")
vault_id = parent_stack.get_output("vault-id")
db_app_id = db_stack.get_output("app-id")
token_broker_app_id = token_broker_stack.get_output("app-id")
file_app_id = file_stack.get_output("app-id")


provider_id = parent_stack.get_output("provider-id")
law_workspace_id = parent_stack.get_output("law-workspace-id")
app_insights_id = parent_stack.get_output("appinsights-id")

db_app_host = db_stack.get_output("domain")
file_app_host = file_stack.get_output("domain")



provider = azuread.Provider("provider", tenant_id=provider_id)

##### Create the app registration and service principal

# There is only a single scope: fetch tokens
scopes: dict[str, str] = {
    "token": "token to impersonate users",
}

# create app roles for the scopes
app_roles: list[azuread.ApplicationAppRoleArgs] = [
    azuread.ApplicationAppRoleArgs(
        id=RandomUuid(f"role-{role}-{mode}-{stack}").result,
        value=f"{role}.{mode}.app",
        display_name=f"{role}.{mode}".title(),
        description=f"{mode} {description}.".capitalize(),
        allowed_member_types=["Application"],
        enabled=True,
    )
    for role, description in scopes.items()
    for mode in ["access"]
]

# create oauth2 permission scopes for the scopes
oauth2_permission_scopes: list[azuread.ApplicationApiOauth2PermissionScopeArgs] = [
    azuread.ApplicationApiOauth2PermissionScopeArgs(
        id=RandomUuid(f"scope-{role}-{mode}-{stack}").result,
        value=f"{role}-{mode}",
        type="User",
        admin_consent_display_name=f"{role}.{mode}".title(),
        admin_consent_description=f"{mode} {description} as the signed-in user.".capitalize(),
        user_consent_display_name=f"{mode} {description}".capitalize(),
        user_consent_description=f"Allow this app to read your {description}.",
        enabled=True,
    )
    for role, description in scopes.items()
    for mode in ["access"]
]

# setup the application registration
email_summarizer_app = azuread.Application(
    get_name("api-app"),
    display_name="email-summarizer",
    sign_in_audience="AzureADMultipleOrgs",
    app_roles=app_roles,
    api=azuread.ApplicationApiArgs(
        requested_access_token_version=2,
        oauth2_permission_scopes=oauth2_permission_scopes,
    ),
    opts=pulumi.ResourceOptions(
        provider=provider,
        ignore_changes=["identifierUris"],
    ),
)

# and create the service principal for it
email_summarizer_app_sp = azuread.ServicePrincipal(
    get_name("sp"),
    client_id=email_summarizer_app.client_id,
    opts=pulumi.ResourceOptions(
        provider=provider,
        depends_on=[email_summarizer_app],
    ),
)

# Also create one in the home tenant
email_summarizer_app_sp_home = azuread.ServicePrincipal(
    get_name("sp", "home-tenant"),
    client_id=email_summarizer_app.client_id,
)

pulumi.export(
    "email-summarizer-sp-home-id",
    email_summarizer_app_sp_home.object_id,
)

pulumi.export(
    "email_summarizer_app_sp",
    email_summarizer_app_sp.object_id,
)

# add a client secret
email_summarizer_app_secret = azuread.ApplicationPassword(
    get_name("secret", "api-app"),
    application_id=email_summarizer_app.object_id.apply(
        lambda v: f"/applications/{v}"
    ),
    display_name="pulumi-generated",
    opts=pulumi.ResourceOptions(
        provider=provider,
        depends_on=[email_summarizer_app],
    ),
)

# give access to global keyvault
keyvault_role_assignment = authorization.RoleAssignment(
    get_name("ra", "kv-sp"),
    principal_id=email_summarizer_app_sp_home.object_id,
    principal_type="ServicePrincipal",
    role_assignment_name=RandomUuid(get_name("ra", "kv")).result,
    role_definition_id=pulumi.Output.format(
        "/subscriptions/{0}/providers/Microsoft.Authorization/roleDefinitions/4633458b-17de-408a-b874-0445c86b69e6",
        client_config.subscription_id,
    ),
    scope=vault_id,
)


# Define the required API permissions as app id -> list of scopes
# ================================================================
# Available scopes by service:
#
# DATABASE SERVICE (database-service):
#   - agent.read.app, agent.write.app           : Agent management
#   - email.read.app, email.write.app           : Email operations
#   - attachment.read.app                       : Email attachments
#   - summary.read.app, summary.write.app       : Summaries
#   - activity-log.write.app                    : Audit trail (REQUIRED for all agents)
#   - project.read.app, project.write.app       : Projects
#   - document.read.app, document.write.app     : Documents
#   - user.read.app, user.write.app             : Users
#   - configuration.read.app                    : Agent configuration
#   - And many more - see database service docs
#
# FILE SERVICE (file-service):
#   - file.read.app                             : Read files (attachments, uploads)
#   - file.write.app                            : Store files
#
# VECTOR DB (vectordb):
#   - vectordb.read.app                         : Read vectors
#   - vectordb.write.app                        : Store vectors
#   - vectordb.search.app                       : Semantic search
#
# TOKEN BROKER (token-broker):
#   - token.access.app                          : REQUIRED for service-to-service auth
#
# MARKDOWN SERVICE (markdown):
#   - convert.app                               : Document conversion
#
# Note: Only request scopes your agent actively uses (principle of least privilege)
api_access = {
    db_app_id: [
        "agent.read.app",
        "activity-log.write.app",  # REQUIRED for all agents — audit trail logging
        "configuration.read.app",  # Read agent configuration
        "email.read.app",          # Read emails via EmailV2Service
        "attachment.read.app",     # Read email attachment metadata
        "summary.read.app",        # Read persisted summaries
        "summary.write.app",       # Write summaries via SummaryService
        "llm.write.app",           # Log LLM interactions (required when using common.llm)
    ],

    file_app_id: ["file.read.app"],  # Read attachment content from file service

    token_broker_app_id: ["token.access.app"],
}

for api_app_id, scopes in api_access.items():
    app = azuread.get_application(
        client_id=api_app_id,
        opts=pulumi.InvokeOptions(
            provider=provider,
        ),
    )
    sp = azuread.get_service_principal(
        client_id=api_app_id,
        opts=pulumi.InvokeOptions(
            provider=provider,
        ),
    )

    for scope in scopes:
        app_role_id = find_app_role_id(app, scope)

        assignment = azuread.AppRoleAssignment(
            f"email-summarizer-{scope.replace('.', '-')}",
            principal_object_id=email_summarizer_app_sp.object_id,
            resource_object_id=sp.object_id,
            app_role_id=app_role_id,
            opts=pulumi.ResourceOptions(provider=provider),
        )

# store relevant secrets in key vault
app_service_app_id_secret = keyvault.Secret(
    get_name("secret", "app-id"),
    properties=keyvault.SecretPropertiesArgs(
        value=email_summarizer_app.client_id
    ),
    resource_group_name=resource_group_name,
    secret_name="agent-email-summarizer-app-id",
    vault_name=vault_name,
)

app_service_secret_secret = keyvault.Secret(
    get_name("secret", "app-secret"),
    properties=keyvault.SecretPropertiesArgs(
        value=email_summarizer_app_secret.value
    ),
    resource_group_name=resource_group_name,
    secret_name="agent-email-summarizer-app-secret",
    vault_name=vault_name,
)

app_id_uri = pulumi.Output.concat("api://", email_summarizer_app.client_id)

identifier_uri = azuread.ApplicationIdentifierUri(
    get_name("uri"),
    application_id=email_summarizer_app.id,
    identifier_uri=app_id_uri,
    opts=pulumi.ResourceOptions(
        provider=provider,
        parent=email_summarizer_app,
        depends_on=[email_summarizer_app],
    ),
)

pulumi.export("app-id", email_summarizer_app.client_id)

################################################################
###
### Anything below here is needed only for staging/production
###
################################################################


if stack != "dev":
    kv_client = SecretClient(
        vault_url=f"https://kv-arata-ai-{stack}.vault.azure.net/",
        credential=DefaultAzureCredential(),
    )

    docker_image = os.environ["DOCKER_IMAGE"]

    ##### Create the web app ######

    # Set up ASP - use the global shared ASP
    app_service_plan_id = parent_stack.get_output("shared-asp-id")
    pulumi.export("asp-id", app_service_plan_id)

    app_name = get_name("app")

    if "prod" in stack:
        host_prefix = "app"
        if stack == "prod":
            short_location = "us"
        elif stack == "prod-india":
            short_location = "india"
        elif stack == "prod-europe":
            short_location = "eu"
        else:
            raise Exception(f"Unknown production stack: {stack}")
    else:
        host_prefix = "app.staging"
        short_location = "us"

    regional_sub_domain = pulumi.Output.all(
        short_location, f"{host_prefix}.arataai.com"
    ).apply(lambda args: f"{args[0]}.{args[1]}")

    if "prod" in stack:
        virtual_network_subnet_id = webapp_subnet_id
        ip_security_restrictions = [
            web.IpSecurityRestrictionArgs(
                name="AllowVNet",
                vnet_subnet_resource_id=webapp_subnet_id,
                action="Allow",
                priority=100,
            ),
            web.IpSecurityRestrictionArgs(
                name="AllowVNet",
                vnet_subnet_resource_id=appgw_subnet_id,
                action="Allow",
                priority=110,
            ),
            web.IpSecurityRestrictionArgs(
                name="AllowVNet",
                vnet_subnet_resource_id=default_subnet_id,
                action="Allow",
                priority=120,
            ),
        ]
        scm_ip_security_restrictions_use_main = False
        scm_ip_security_restrictions_default_action = "Deny"
        ip_security_restrictions_default_action = "Deny"
        public_network_access = "Disabled"
    else:
        virtual_network_subnet_id = None
        ip_security_restrictions = None
        scm_ip_security_restrictions_use_main = None
        scm_ip_security_restrictions_default_action = "Allow"
        ip_security_restrictions_default_action = "Allow"
        public_network_access = "Enabled"

    credential = DefaultAzureCredential()
    kv_client = SecretClient(
        vault_url=f"https://kv-arata-ai-{stack}.vault.azure.net/",
        credential=credential,
    )
    auth0_domain = kv_client.get_secret("auth0-domain")
    auth0_client_id = kv_client.get_secret("auth0-client-id")
    auth0_client_secret = kv_client.get_secret("auth0-client-secret")
    auth0_session_secret = kv_client.get_secret("ui-cookie-secret")

    app_settings = [
        web.NameValuePairArgs(name="KEY_VAULT_NAME", value=vault_name),
        web.NameValuePairArgs(
            name="AZURE_KEYVAULT_URI",
            value=vault_name.apply(
                lambda v: f"https://{v}.vault.azure.net/"
            ),
        ),
        web.NameValuePairArgs(
            name="AZURE_TENANT_ID", value=provider_id
        ),
        web.NameValuePairArgs(
            name="AZURE_CLIENT_ID",
            value=email_summarizer_app.client_id,
        ),
        web.NameValuePairArgs(
            name="AZURE_CLIENT_SECRET",
            value=app_service_secret_secret.properties.apply(
                lambda p: f"@Microsoft.KeyVault(SecretUri={p.secret_uri_with_version})"
            ),
        ),
        web.NameValuePairArgs(
            name="SERVER_URL",
            value=f"https://{app_name}.azurewebsites.net",
        ),
        web.NameValuePairArgs(
            name="ARATA_DB_URL",
            value=db_app_host.apply(lambda v: f"https://{v}"),
        ),
        web.NameValuePairArgs(
            name="AZURE_DB_SERVICE",
            value="db-service",
        ),
        web.NameValuePairArgs(
            name="AZURE_CALLER_SERVICE",
            value="applications-email-summarizer",
        ),


        web.NameValuePairArgs(
            name="FILE_SERVICE_URL",
            value=file_app_host.apply(
                lambda v: f"https://{v}/v1"
            ),
        ),
        web.NameValuePairArgs(
            name="AZURE_FILE_SERVICE",
            value="file-service",
        ),

        web.NameValuePairArgs(
            name="AUTH0_DOMAIN", value=auth0_domain.value
        ),
        web.NameValuePairArgs(
            name="AUTH0_CLIENT_ID", value=auth0_client_id.value
        ),
        web.NameValuePairArgs(
            name="AUTH0_CLIENT_SECRET",
            value=f"@Microsoft.KeyVault(SecretUri={auth0_client_secret.id})",
        ),
        web.NameValuePairArgs(
            name="AUTH0_SCOPE",
            value="openid profile email offline_access",
        ),
        web.NameValuePairArgs(
            name="EMAIL_SUMMARIZER_APP_URL",
            value=regional_sub_domain.apply(
                lambda d: f"https://{d}{APP_PATH}"
            ),
        ),
        web.NameValuePairArgs(
            name="HOME_APP_URL",
            value=regional_sub_domain.apply(
                lambda d: f"https://{d}"
            ),
        ),
        web.NameValuePairArgs(
            name="AUTH0_AUDIENCE",
            value=f"https://{auth0_domain.value}/api/v2/",
        ),
        web.NameValuePairArgs(
            name="AUTH0_SESSION_SECRET",
            value=f"@Microsoft.KeyVault(SecretUri={auth0_session_secret.id})",
        ),
        web.NameValuePairArgs(name="NODE_ENV", value="production"),
    ]

    app_service = web.WebApp(
        app_name,
        kind="app,linux,container",
        name=app_name,
        resource_group_name=resource_group_name,
        server_farm_id=app_service_plan_id,
        site_config=web.SiteConfigArgs(
            acr_use_managed_identity_creds=True,
            acr_user_managed_identity_id=managed_identity_client_id,
            key_vault_reference_identity=managed_identity_id,
            linux_fx_version=acr.apply(lambda repo: f"DOCKER|{docker_image}"),
            app_settings=app_settings,
            ip_security_restrictions=ip_security_restrictions,
            scm_ip_security_restrictions_use_main=scm_ip_security_restrictions_use_main,
            scm_ip_security_restrictions_default_action=scm_ip_security_restrictions_default_action,
            ip_security_restrictions_default_action=ip_security_restrictions_default_action,
        ),
        virtual_network_subnet_id=virtual_network_subnet_id,
        public_network_access=public_network_access,
        key_vault_reference_identity=managed_identity_id,
        identity=web.ManagedServiceIdentityArgs(
            type="UserAssigned",
            user_assigned_identities=[managed_identity_id],
        ),
        tags=common_tags,
        https_only=True,
    )

    pulumi.export("domain", app_service.default_host_name)

    ##### Register app in App Configuration for gateway routing #####

    def register_app_to_config(fqdn: str):
        """Register this app's routing info to App Configuration for gateway discovery."""
        entries = {
            f"apps:{APP_NAME}:fqdn": fqdn,
            f"apps:{APP_NAME}:path": APP_PATH,
            f"apps:{APP_NAME}:priority": str(APP_PRIORITY),
            f"apps:{APP_NAME}:rewrite": APP_REWRITE,
        }
        for key, value in entries.items():
            appconfiguration.KeyValue(
                f"cfg-{APP_NAME}-{key}",
                config_store_name=app_config_name,
                resource_group_name=resource_group_name,
                key_value_name=f"{key}${stack}",
                value=value,
            )

    # Register after app service is created
    app_service.default_host_name.apply(register_app_to_config)

    ##### Private Endpoint (prod only) #####

    if "prod" in stack:
        webapp_private_endpoint = network.PrivateEndpoint(
            get_name("pe", "webapp"),
            resource_group_name=resource_group_name,
            subnet=network.SubnetArgs(id=default_subnet_id),
            location=app_service.location,
            private_link_service_connections=[
                network.PrivateLinkServiceConnectionArgs(
                    name=get_name("plsconn", "webapp"),
                    private_link_service_id=app_service.id,
                    group_ids=["sites"],
                )
            ],
            tags=common_tags,
        )

        dns_group = network.PrivateDnsZoneGroup(
            get_name("endpoint-dns-group"),
            resource_group_name=resource_group_name,
            private_endpoint_name=webapp_private_endpoint.name,
            private_dns_zone_configs=[
                network.PrivateDnsZoneConfigArgs(
                    name="config1",
                    private_dns_zone_id=webapp_dns_zone_id,
                )
            ],
        )

        pe_ip = webapp_private_endpoint.custom_dns_configs.apply(
            lambda configs: configs[0].ip_addresses[0]
            if configs and configs[0].ip_addresses
            else None
        )
        pulumi.export("webapp-private-endpoint-ip", pe_ip)

    ##### Diagnostics and Logging #####

    app_service_logs = web.WebAppDiagnosticLogsConfiguration(
        get_name("app-logs"),
        name=get_name("app"),
        resource_group_name=resource_group_name,
        application_logs=web.ApplicationLogsConfigArgs(
            file_system=web.FileSystemApplicationLogsConfigArgs(level="Verbose")
        ),
        http_logs=web.HttpLogsConfigArgs(
            file_system=web.FileSystemHttpLogsConfigArgs(
                enabled=True, retention_in_days=7, retention_in_mb=35
            )
        ),
        opts=pulumi.ResourceOptions(depends_on=[app_service]),
    )

    app_service_domain_secret = keyvault.Secret(
        get_name("secret", "email-summarizer-domain"),
        properties=keyvault.SecretPropertiesArgs(
            value=app_service.default_host_name
        ),
        resource_group_name=resource_group_name,
        secret_name="email-summarizer-domain",
        vault_name=vault_name,
    )

    # Diagnostic setting to link webapp to Log Analytics workspace
    app_service_diagnostic_setting = monitor.DiagnosticSetting(
        get_name("diag", "webapp-law"),
        name=get_name("diag", "webapp-law"),
        resource_uri=app_service.id,
        workspace_id=law_workspace_id,
        logs=[
            monitor.LogSettingsArgs(
                category_group="allLogs",
                enabled=True,
            )
        ],
        metrics=[
            monitor.MetricSettingsArgs(
                category="AllMetrics",
                enabled=True,
            ),
        ],
    )

    # StandardWebTest for /ping endpoint
    ping_url = app_service.default_host_name.apply(
        lambda host: f"https://{host}/ping"
    )
    standard_web_test = azure.appinsights.StandardWebTest(
        get_name("webtest", "ping"),
        name=get_name("webtest", "ping"),
        resource_group_name=resource_group_name,
        application_insights_id=app_insights_id,
        geo_locations=["us-va-ash-azr"],
        request=azure.appinsights.StandardWebTestRequestArgs(
            url=ping_url,
            http_verb="POST",
        ),
        frequency=300,
        timeout=30,
        enabled=True,
        opts=pulumi.ResourceOptions(depends_on=[app_service]),
    )

