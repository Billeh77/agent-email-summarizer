from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.keyvault.secrets import SecretClient


def get_token(caller: str, audience: str, environment: str = "dev"):
    kv_uri = f"https://kv-arata-ai-{environment}.vault.azure.net"

    credential = DefaultAzureCredential(
        additionally_allowed_tenants=["dc9249f1-89a1-4c43-8e22-c55df13f5937"]
    )

    client = SecretClient(vault_url=kv_uri, credential=credential)

    tenant_id = client.get_secret("entra-tenant-id").value

    # Fetch caller credentials
    try:
        client_id = client.get_secret(f"{caller}-app-id").value
        client_secret = client.get_secret(f"{caller}-app-secret").value
    except Exception:
        print(
            f"Error retrieving secrets for calling service '{caller}'. "
            "This should correspond to the target service name. "
            "You can check the exact name in the key vault; you "
            "should see a key '<service-name>-app-id'."
        )
        return

    # Fetch audience app id
    try:
        audience_id = client.get_secret(f"{audience}-app-id").value
    except Exception:
        print(
            f"Error retrieving secret for audience '{audience}'. "
            "This should correspond to the target service name. "
            "You can check the exact name in the key vault; you "
            "should see a key '<service-name>-app-id'."
        )
        return

    # Generate the token
    cred = ClientSecretCredential(tenant_id, client_id, client_secret)
    token = cred.get_token(f"api://{audience_id}/.default")
    access_token = token.token

    print(f"Access Token: {access_token}")
    return access_token


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print(
            "Usage: python generate_token <caller> <audience> <dev, staging, prod...(optional)>"
        )
        sys.exit(1)

    caller = sys.argv[1]
    audience = sys.argv[2]
    environment = sys.argv[3] if len(sys.argv) == 4 else "dev"

    get_token(caller, audience, environment)
